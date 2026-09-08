"""Parcours documentaire de prise en charge d'urgence MHC.

Règles (Référentiel documentaire MHC) :
- Après décision médecin-conseil : BPCU XOR BRPCU (clôture).
- Après BPCU / BH / BPH : bulletin de sortie, hospitalisation/prolongation, ou sortie + rapatriement sanitaire.
- BRS jamais seul : toujours émis avec un bulletin de sortie (mode rapatriement sanitaire).
- Décès : branche parallèle BRF puis ARF, à tout moment.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy.orm import Session, selectinload

from app.core.mhc_nomenclature import (
    DOCUMENT_TITLES,
    DOCUMENT_VALIDITY_HOURS,
    MhcCareDocumentStatus,
    MhcCareDocumentType,
    MhcExitMode,
    parse_order_from_reference,
)
from app.models.alerte import Alerte
from app.models.hospital import Hospital
from app.models.hospital_stay import HospitalStay
from app.models.mhc_care_document import MhcCareDocument
from app.models.produit_assurance import ProduitAssurance
from app.models.sinistre import Sinistre
from app.models.souscription import Souscription
from app.models.user import User
from app.core.enums import Role
from app.services.mhc_reference_service import allocate_document_number

CLOSING_TYPES = {
    MhcCareDocumentType.BRPCU,
    MhcCareDocumentType.ARS,
    MhcCareDocumentType.ARF,
}

# --- États de validation (référentiel documentaire MHC, colonne « Validé par ») ---
VALIDATION_NOT_REQUIRED = "non_requise"
VALIDATION_PENDING = "en_attente"
VALIDATION_APPROVED = "valide"
VALIDATION_REFUSED = "refuse"

# Un document est « effectif » (compte dans l'enchaînement, déclenche la suite)
# uniquement s'il ne requiert pas de validation ou si toutes ont été obtenues.
EFFECTIVE_VALIDATION_STATUSES = {VALIDATION_NOT_REQUIRED, VALIDATION_APPROVED}


class CareDocumentPermissionError(ValueError):
    """Rôle non autorisé pour émettre ou valider un document (→ HTTP 403)."""


# --- Groupes d'acteurs (cartographie référentiel → rôles applicatifs) ---
# Médecin-conseil  → MEDECIN_REFERENT_MH
# Partenaire-Santé → MEDECIN_HOPITAL / HOSPITAL_ADMIN / AGENT_RECEPTION_HOPITAL
# Pôle médical MHC → MEDICAL_REVIEWER
GROUP_MEDECIN_CONSEIL = "medecin_conseil"
GROUP_PARTENAIRE_SANTE = "partenaire_sante"
GROUP_POLE_MEDICAL_MHC = "pole_medical_mhc"

GROUP_LABELS: Dict[str, str] = {
    GROUP_MEDECIN_CONSEIL: "Médecin-conseil",
    GROUP_PARTENAIRE_SANTE: "Partenaire-Santé",
    GROUP_POLE_MEDICAL_MHC: "Pôle médical MHC",
}

GROUP_ROLES: Dict[str, set] = {
    GROUP_MEDECIN_CONSEIL: {Role.MEDECIN_REFERENT_MH},
    GROUP_PARTENAIRE_SANTE: {Role.MEDECIN_HOPITAL, Role.HOSPITAL_ADMIN, Role.AGENT_RECEPTION_HOPITAL},
    GROUP_POLE_MEDICAL_MHC: {Role.MEDICAL_REVIEWER},
}

# Émetteur autorisé par type de document (colonne « Émis »).
DOCUMENT_EMITTERS: Dict[MhcCareDocumentType, str] = {
    MhcCareDocumentType.BPCU: GROUP_MEDECIN_CONSEIL,
    MhcCareDocumentType.BRPCU: GROUP_MEDECIN_CONSEIL,
    MhcCareDocumentType.BS: GROUP_PARTENAIRE_SANTE,
    MhcCareDocumentType.BH: GROUP_PARTENAIRE_SANTE,
    MhcCareDocumentType.BPH: GROUP_PARTENAIRE_SANTE,
    MhcCareDocumentType.BRS: GROUP_MEDECIN_CONSEIL,
    MhcCareDocumentType.ARS: GROUP_POLE_MEDICAL_MHC,
    MhcCareDocumentType.BRF: GROUP_MEDECIN_CONSEIL,
    MhcCareDocumentType.ARF: GROUP_POLE_MEDICAL_MHC,
}

# Groupes validateurs requis par type de document (colonne « Validé par »).
# Liste vide = aucune validation (NÉANT). Deux groupes = double validation.
DOCUMENT_VALIDATORS: Dict[MhcCareDocumentType, List[str]] = {
    MhcCareDocumentType.BPCU: [],
    MhcCareDocumentType.BRPCU: [GROUP_POLE_MEDICAL_MHC],
    MhcCareDocumentType.BS: [],
    MhcCareDocumentType.BH: [GROUP_MEDECIN_CONSEIL, GROUP_POLE_MEDICAL_MHC],
    MhcCareDocumentType.BPH: [GROUP_MEDECIN_CONSEIL, GROUP_POLE_MEDICAL_MHC],
    MhcCareDocumentType.BRS: [GROUP_POLE_MEDICAL_MHC, GROUP_PARTENAIRE_SANTE],
    MhcCareDocumentType.ARS: [],
    MhcCareDocumentType.BRF: [GROUP_POLE_MEDICAL_MHC],
    MhcCareDocumentType.ARF: [],
}


def _role_value(user: Optional[User]) -> Optional[str]:
    role = getattr(user, "role", None)
    return getattr(role, "value", role)


def _is_admin(user: Optional[User]) -> bool:
    if user is None:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return _role_value(user) == Role.ADMIN.value


def _in_group(user: Optional[User], group: str) -> bool:
    role_val = _role_value(user)
    if role_val is None:
        return False
    return any(role_val == r.value for r in GROUP_ROLES.get(group, set()))


def required_validator_groups(doc_type: MhcCareDocumentType) -> List[str]:
    return list(DOCUMENT_VALIDATORS.get(doc_type, []))


def _ensure_emitter(actor: Optional[User], doc_type: MhcCareDocumentType) -> None:
    if _is_admin(actor):
        return
    group = DOCUMENT_EMITTERS.get(doc_type)
    if group and not _in_group(actor, group):
        raise CareDocumentPermissionError(
            f"Seul le rôle « {GROUP_LABELS[group]} » peut émettre « {DOCUMENT_TITLES[doc_type]} »."
        )


def _now() -> datetime:
    return datetime.utcnow()


def _as_type(value: str | MhcCareDocumentType) -> MhcCareDocumentType:
    if isinstance(value, MhcCareDocumentType):
        return value
    return MhcCareDocumentType(str(value))


def _docs(sinistre: Sinistre) -> List[MhcCareDocument]:
    return list(getattr(sinistre, "care_documents", None) or [])


def _has_type(docs: Iterable[MhcCareDocument], doc_type: MhcCareDocumentType) -> bool:
    return any(d.document_type == doc_type.value for d in docs)


def _latest(docs: Iterable[MhcCareDocument], doc_type: MhcCareDocumentType) -> Optional[MhcCareDocument]:
    matches = [d for d in docs if d.document_type == doc_type.value]
    if not matches:
        return None
    return sorted(matches, key=lambda d: d.issued_at or d.created_at)[-1]


def _dossier_closed(docs: Iterable[MhcCareDocument]) -> bool:
    for doc in docs:
        if doc.document_type in {t.value for t in CLOSING_TYPES}:
            return True
        if doc.document_type == MhcCareDocumentType.BS.value:
            payload = doc.payload or {}
            if payload.get("mode_sortie") != MhcExitMode.RAPATRIEMENT_SANITAIRE.value:
                return True
    return False


def _expire_if_needed(doc: MhcCareDocument) -> None:
    if doc.valid_until and doc.statut == MhcCareDocumentStatus.EMI.value and doc.valid_until < _now():
        doc.statut = MhcCareDocumentStatus.EXPIRE.value


def _effective(docs: Iterable[MhcCareDocument]) -> List[MhcCareDocument]:
    """Documents qui comptent dans l'enchaînement : validés ou sans validation requise."""
    return [d for d in docs if (d.validation_status or VALIDATION_NOT_REQUIRED) in EFFECTIVE_VALIDATION_STATUSES]


def _pending(docs: Iterable[MhcCareDocument]) -> List[MhcCareDocument]:
    return [d for d in docs if (d.validation_status or VALIDATION_NOT_REQUIRED) == VALIDATION_PENDING]


def _compute_next(docs: Sequence[MhcCareDocument], numero_sinistre: Optional[str]) -> List[str]:
    """Actions possibles à partir des documents EFFECTIFS (indépendamment des validations en attente)."""
    if _has_type(docs, MhcCareDocumentType.ARF):
        return []
    if _has_type(docs, MhcCareDocumentType.ARS):
        return []
    if _has_type(docs, MhcCareDocumentType.BRPCU):
        return []
    if _has_type(docs, MhcCareDocumentType.BRF):
        return [MhcCareDocumentType.ARF.value]
    if _has_type(docs, MhcCareDocumentType.BRS) and not _has_type(docs, MhcCareDocumentType.ARS):
        return [MhcCareDocumentType.ARS.value, MhcCareDocumentType.BRF.value]

    if _has_type(docs, MhcCareDocumentType.BS):
        bs = _latest(docs, MhcCareDocumentType.BS)
        mode = (bs.payload or {}).get("mode_sortie") if bs else None
        if mode == MhcExitMode.RAPATRIEMENT_SANITAIRE.value and not _has_type(docs, MhcCareDocumentType.BRS):
            return [MhcCareDocumentType.BRS.value, MhcCareDocumentType.BRF.value]
        return [MhcCareDocumentType.BRF.value] if not _dossier_closed(docs) else []

    if _has_type(docs, MhcCareDocumentType.BPH) or _has_type(docs, MhcCareDocumentType.BH):
        return [
            MhcCareDocumentType.BPH.value,
            MhcCareDocumentType.BS.value,
            MhcCareDocumentType.BRF.value,
        ]
    if _has_type(docs, MhcCareDocumentType.BPCU):
        return [
            MhcCareDocumentType.BH.value,
            MhcCareDocumentType.BS.value,
            MhcCareDocumentType.BRF.value,
        ]
    return [
        MhcCareDocumentType.BPCU.value,
        MhcCareDocumentType.BRPCU.value,
        MhcCareDocumentType.BRF.value,
    ]


def allowed_next_actions(sinistre: Sinistre) -> List[str]:
    docs = _docs(sinistre)
    for doc in docs:
        _expire_if_needed(doc)

    effective = _effective(docs)
    actions = _compute_next(effective, sinistre.numero_sinistre)

    # Tant qu'une validation est en attente, on bloque les émissions concurrentes.
    # Seule la branche décès (BRF) reste ouverte, et jamais pour un type déjà en attente.
    pending = _pending(docs)
    if pending:
        pending_types = {d.document_type for d in pending}
        actions = [
            a for a in actions
            if a == MhcCareDocumentType.BRF.value and a not in pending_types
        ]
    return actions


def pending_validation_documents(sinistre: Sinistre) -> List[MhcCareDocument]:
    return _pending(_docs(sinistre))


def _require_allowed(sinistre: Sinistre, doc_type: MhcCareDocumentType) -> None:
    allowed = allowed_next_actions(sinistre)
    if doc_type.value not in allowed:
        titres = ", ".join(DOCUMENT_TITLES[MhcCareDocumentType(a)] for a in allowed) or "aucun"
        raise ValueError(
            f"Le document « {DOCUMENT_TITLES[doc_type]} » n'est pas autorisé à ce stade. "
            f"Actions possibles : {titres}."
        )


def _build_party_snapshot(sinistre: Sinistre) -> Dict[str, Any]:
    alerte = getattr(sinistre, "alerte", None)
    souscription = getattr(sinistre, "souscription", None)
    user = None
    if alerte is not None:
        user = getattr(alerte, "user", None)
    if user is None and souscription is not None:
        user = getattr(souscription, "user", None)
    hospital: Optional[Hospital] = getattr(sinistre, "hospital", None)
    produit = getattr(souscription, "produit_assurance", None) if souscription else None
    assureur_nom = None
    if produit is not None:
        assureur_nom = getattr(getattr(produit, "assureur_obj", None), "nom", None) or produit.assureur
    snapshot = {
        "numero_sinistre": sinistre.numero_sinistre,
        "numero_police": getattr(souscription, "numero_souscription", None) if souscription else None,
        "voyageur": {
            "nom": getattr(user, "full_name", None),
            "date_naissance": str(getattr(user, "date_naissance", "") or ""),
            "genre": getattr(user, "sexe", None),
            "nationalite": getattr(user, "nationalite", None),
            "passeport": getattr(user, "numero_passeport", None),
            "pays_residence": getattr(user, "pays_residence", None),
            "telephone": getattr(user, "telephone", None),
            "email": getattr(user, "email", None),
            "contact_urgence": getattr(user, "nom_contact_urgence", None),
        },
        "partenaire_sante": {
            "nom": getattr(hospital, "nom", None) if hospital else None,
            "ville": getattr(hospital, "ville", None) if hospital else None,
            "pays": getattr(hospital, "pays", None) if hospital else None,
            "telephone": getattr(hospital, "telephone", None) if hospital else None,
            "email": getattr(hospital, "email", None) if hospital else None,
        },
        "assureur": {
            "compagnie": assureur_nom,
            "plafond": str(getattr(produit, "cout", "") or "") if produit else None,
            "date_debut": str(getattr(souscription, "date_debut", "") or "") if souscription else None,
            "date_fin": str(getattr(souscription, "date_fin", "") or "") if souscription else None,
        },
    }
    return snapshot


def _doctor_display(user: Optional[User]) -> Optional[str]:
    if not user:
        return None
    return getattr(user, "full_name", None) or getattr(user, "email", None) or getattr(user, "username", None)


def _enrich_payload_from_sinistre(
    sinistre: Sinistre,
    doc_type: MhcCareDocumentType,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Complète le payload utilisateur avec les données du séjour et du dossier."""
    enriched = dict(payload or {})
    stay: Optional[HospitalStay] = getattr(sinistre, "hospital_stay", None)
    alerte = getattr(sinistre, "alerte", None)

    if stay:
        doctor_name = _doctor_display(getattr(stay, "assigned_doctor", None))
        if doctor_name and not enriched.get("medecin_traitant"):
            enriched["medecin_traitant"] = doctor_name
        if stay.service_concerne and not enriched.get("service"):
            enriched["service"] = stay.service_concerne
        if stay.chambre and not enriched.get("chambre"):
            enriched["chambre"] = stay.chambre

        motif = stay.report_motif_hospitalisation or stay.report_motif_consultation
        if motif:
            enriched.setdefault("motif_medical", motif)
            enriched.setdefault("diagnostic", motif)

        if stay.started_at:
            started = stay.started_at.isoformat()
            enriched.setdefault("admission_prevue", started)
            enriched.setdefault("date_entree", stay.started_at.strftime("%Y-%m-%d %H:%M"))
        if stay.ended_at:
            enriched.setdefault("date_sortie", stay.ended_at.strftime("%Y-%m-%d %H:%M"))
        if stay.report_duree_sejour_heures is not None and not enriched.get("duree_jours"):
            enriched["duree_jours"] = str(round(stay.report_duree_sejour_heures / 24, 1))
        if stay.report_resume and not enriched.get("resume_rapport"):
            enriched["resume_rapport"] = stay.report_resume
        if stay.report_examens and not enriched.get("examens_prevus"):
            examens = stay.report_examens
            if isinstance(examens, list):
                enriched["examens_prevus"] = ", ".join(str(x) for x in examens)

    referent_name = _doctor_display(getattr(sinistre, "medecin_referent", None))
    if referent_name:
        enriched.setdefault("medecin_referent", referent_name)

    if alerte and alerte.description:
        enriched.setdefault("motif_medical", alerte.description)
        enriched.setdefault("diagnostic", alerte.description)

    if doc_type == MhcCareDocumentType.BH and stay and stay.started_at and not enriched.get("admission_prevue"):
        enriched["admission_prevue"] = stay.started_at.isoformat()

    partenaire = dict(enriched.get("partenaire_sante") or {})
    if enriched.get("service"):
        partenaire.setdefault("service", enriched["service"])
    if enriched.get("medecin_traitant"):
        partenaire.setdefault("medecin_referent", enriched["medecin_traitant"])
    if partenaire:
        enriched["partenaire_sante"] = partenaire

    return enriched


def _related_numbers(docs: Sequence[MhcCareDocument]) -> Dict[str, Optional[str]]:
    return {
        "numero_bpcu": (_latest(docs, MhcCareDocumentType.BPCU).numero if _latest(docs, MhcCareDocumentType.BPCU) else None),
        "numero_brpcu": (_latest(docs, MhcCareDocumentType.BRPCU).numero if _latest(docs, MhcCareDocumentType.BRPCU) else None),
        "numero_bh": (_latest(docs, MhcCareDocumentType.BH).numero if _latest(docs, MhcCareDocumentType.BH) else None),
        "numero_bph": (_latest(docs, MhcCareDocumentType.BPH).numero if _latest(docs, MhcCareDocumentType.BPH) else None),
        "numero_bs": (_latest(docs, MhcCareDocumentType.BS).numero if _latest(docs, MhcCareDocumentType.BS) else None),
        "numero_brs": (_latest(docs, MhcCareDocumentType.BRS).numero if _latest(docs, MhcCareDocumentType.BRS) else None),
        "numero_brf": (_latest(docs, MhcCareDocumentType.BRF).numero if _latest(docs, MhcCareDocumentType.BRF) else None),
    }


def _create_document(
    db: Session,
    sinistre: Sinistre,
    doc_type: MhcCareDocumentType,
    actor: Optional[User],
    payload: Optional[Dict[str, Any]] = None,
    parent: Optional[MhcCareDocument] = None,
    notes: Optional[str] = None,
) -> MhcCareDocument:
    docs = _docs(sinistre)
    bh = _latest(docs, MhcCareDocumentType.BH)
    bh_order = parse_order_from_reference(bh.numero) if bh else None
    bph_sequence = None
    if doc_type == MhcCareDocumentType.BPH:
        existing = [d for d in docs if d.document_type == MhcCareDocumentType.BPH.value]
        bph_sequence = len(existing) + 1
        if not bh_order:
            raise ValueError("Un bon d'hospitalisation est requis avant une prolongation.")

    issued_at = _now()
    hours = DOCUMENT_VALIDITY_HOURS.get(doc_type)
    valid_until = issued_at + timedelta(hours=hours) if hours else None
    numero = allocate_document_number(
        db,
        doc_type,
        sinistre,
        bh_order=bh_order,
        bph_sequence=bph_sequence,
    )
    snapshot = _build_party_snapshot(sinistre)
    snapshot.update(_related_numbers(docs))
    user_payload = _enrich_payload_from_sinistre(sinistre, doc_type, payload)
    merged_payload = {**snapshot, **user_payload}
    merged_payload["heure_emission"] = issued_at.strftime("%H:%M")
    merged_payload["date_emission"] = issued_at.strftime("%Y-%m-%d")
    if valid_until:
        merged_payload["valable_jusqu_au"] = valid_until.isoformat()

    validators = required_validator_groups(doc_type)
    validation_status = VALIDATION_PENDING if validators else VALIDATION_NOT_REQUIRED

    document = MhcCareDocument(
        sinistre_id=sinistre.id,
        document_type=doc_type.value,
        numero=numero,
        statut=MhcCareDocumentStatus.EMI.value,
        issued_at=issued_at,
        valid_until=valid_until,
        issued_by_id=actor.id if actor else None,
        parent_document_id=parent.id if parent else None,
        payload=merged_payload,
        notes=notes,
        validation_status=validation_status,
        validations=[],
    )
    db.add(document)
    db.flush()
    sinistre.care_documents.append(document)
    return document


def _close_dossier(sinistre: Sinistre, alerte: Optional[Alerte]) -> None:
    sinistre.statut = "resolu"
    if alerte and alerte.statut not in {"annulee"}:
        alerte.statut = "resolue"


def issue_care_document(
    db: Session,
    sinistre: Sinistre,
    document_type: str,
    actor: Optional[User],
    payload: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None,
    alerte: Optional[Alerte] = None,
    enforce_roles: bool = True,
) -> List[MhcCareDocument]:
    doc_type = _as_type(document_type)
    payload = dict(payload or {})
    alerte = alerte or getattr(sinistre, "alerte", None)

    # Contrôle du rôle émetteur (colonne « Émis » du référentiel).
    if enforce_roles:
        _ensure_emitter(actor, doc_type)

    if not sinistre.numero_sinistre and doc_type != MhcCareDocumentType.BRF:
        raise ValueError("Le numéro de sinistre doit être attribué avant l'émission d'un bon.")

    created: List[MhcCareDocument] = []

    if doc_type == MhcCareDocumentType.BS:
        mode = payload.get("mode_sortie") or MhcExitMode.GUERISON.value
        payload["mode_sortie"] = mode
        _require_allowed(sinistre, MhcCareDocumentType.BS)
        bulletin = _create_document(db, sinistre, MhcCareDocumentType.BS, actor, payload, notes=notes)
        created.append(bulletin)
        if mode == MhcExitMode.RAPATRIEMENT_SANITAIRE.value:
            # Le BRS est généré simultanément (companion) : c'est un effet du BS en
            # mode rapatriement, on ne réapplique donc pas le contrôle d'émetteur.
            # Il reste soumis à sa propre validation (Pôle médical MHC + Partenaire-Santé).
            brs = _create_document(
                db,
                sinistre,
                MhcCareDocumentType.BRS,
                actor,
                payload,
                parent=bulletin,
                notes=notes,
            )
            created.append(brs)
        else:
            # Bulletin de sortie simple : aucune validation requise → clôture immédiate.
            _close_dossier(sinistre, alerte)
        return created

    _require_allowed(sinistre, doc_type)
    document = _create_document(db, sinistre, doc_type, actor, payload, notes=notes)
    created.append(document)

    # Les effets de clôture ne s'appliquent que si le document est effectif dès
    # l'émission (aucune validation requise). Pour les documents à valider (ex.
    # BRPCU), la clôture est différée à la validation (voir validate_care_document).
    if doc_type in CLOSING_TYPES and document.validation_status == VALIDATION_NOT_REQUIRED:
        _apply_effective_effects(sinistre, document, alerte)
    return created


def _apply_effective_effects(
    sinistre: Sinistre,
    document: MhcCareDocument,
    alerte: Optional[Alerte],
) -> None:
    """Applique les effets « métier » quand un document devient effectif."""
    doc_type = _as_type(document.document_type)
    if doc_type == MhcCareDocumentType.BRPCU:
        sinistre.statut = "annule"
        if alerte:
            alerte.statut = "annulee"
    elif doc_type in {MhcCareDocumentType.ARS, MhcCareDocumentType.ARF}:
        _close_dossier(sinistre, alerte)


def validate_care_document(
    db: Session,
    sinistre: Sinistre,
    document: MhcCareDocument,
    actor: Optional[User],
    approve: bool,
    notes: Optional[str] = None,
    alerte: Optional[Alerte] = None,
    enforce_roles: bool = True,
) -> MhcCareDocument:
    """Valide (ou refuse) un document en attente.

    Gère la validation simple et la double validation (deux groupes requis, ex.
    BH/BPH : Médecin-conseil + Pôle médical MHC ; BRS : Pôle médical MHC +
    Partenaire-Santé). Le document devient effectif une fois tous les groupes
    requis ayant approuvé ; un seul refus le met en statut « refuse ».
    """
    doc_type = _as_type(document.document_type)
    alerte = alerte or getattr(sinistre, "alerte", None)

    if (document.validation_status or VALIDATION_NOT_REQUIRED) != VALIDATION_PENDING:
        raise ValueError("Ce document n'est pas en attente de validation.")

    required = required_validator_groups(doc_type)
    actor_groups = [g for g in required if _in_group(actor, g)]
    if enforce_roles and not _is_admin(actor) and not actor_groups:
        labels = " + ".join(GROUP_LABELS[g] for g in required) or "aucun"
        raise CareDocumentPermissionError(
            f"Seul(s) « {labels} » peut/peuvent valider « {DOCUMENT_TITLES[doc_type]} »."
        )

    validations = list(document.validations or [])
    approved_groups = {v.get("groupe") for v in validations if v.get("approuve")}
    actor_name = _doctor_display(actor)

    if not approve:
        validations.append({
            "groupe": actor_groups[0] if actor_groups else "admin",
            "user_id": getattr(actor, "id", None),
            "user_name": actor_name,
            "approuve": False,
            "notes": notes,
            "at": _now().isoformat(),
        })
        document.validations = validations
        document.validation_status = VALIDATION_REFUSED
        return document

    # Approbation : un admin peut valider tous les groupes restants, sinon
    # uniquement son/ses groupe(s).
    groups_to_record = actor_groups or (required if _is_admin(actor) else [])
    for group in groups_to_record:
        if group in approved_groups:
            continue
        validations.append({
            "groupe": group,
            "user_id": getattr(actor, "id", None),
            "user_name": actor_name,
            "approuve": True,
            "notes": notes,
            "at": _now().isoformat(),
        })
        approved_groups.add(group)
    document.validations = validations

    if all(g in approved_groups for g in required):
        document.validation_status = VALIDATION_APPROVED
        document.validated_at = _now()
        _apply_effective_effects(sinistre, document, alerte)
    return document


def issue_decision_documents(
    db: Session,
    sinistre: Sinistre,
    approve: bool,
    actor: Optional[User],
    notes: Optional[str] = None,
    alerte: Optional[Alerte] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> List[MhcCareDocument]:
    """Émet automatiquement BPCU (acceptation) ou BRPCU (refus) après décision médicale."""
    docs = _docs(sinistre)
    if _has_type(docs, MhcCareDocumentType.BPCU) or _has_type(docs, MhcCareDocumentType.BRPCU):
        return []
    doc_type = MhcCareDocumentType.BPCU if approve else MhcCareDocumentType.BRPCU
    # Chemin système : l'émission est déclenchée par la vérification d'urgence
    # (déjà autorisée en amont pour le médecin-conseil), on ne réapplique donc
    # pas le contrôle de rôle émetteur ici.
    return issue_care_document(
        db,
        sinistre,
        doc_type.value,
        actor,
        payload=payload,
        notes=notes,
        alerte=alerte,
        enforce_roles=False,
    )


def list_care_documents(db: Session, sinistre_id: int) -> List[MhcCareDocument]:
    return (
        db.query(MhcCareDocument)
        .filter(MhcCareDocument.sinistre_id == sinistre_id)
        .order_by(MhcCareDocument.issued_at.asc(), MhcCareDocument.id.asc())
        .all()
    )


def get_care_document(db: Session, document_id: int) -> Optional[MhcCareDocument]:
    return db.query(MhcCareDocument).filter(MhcCareDocument.id == document_id).first()


def load_sinistre_for_care(db: Session, sinistre_id: int) -> Optional[Sinistre]:
    return (
        db.query(Sinistre)
        .options(
            selectinload(Sinistre.care_documents),
            selectinload(Sinistre.hospital),
            selectinload(Sinistre.medecin_referent),
            selectinload(Sinistre.hospital_stay).selectinload(HospitalStay.assigned_doctor),
            selectinload(Sinistre.souscription).selectinload(Souscription.user),
            selectinload(Sinistre.souscription).selectinload(Souscription.produit_assurance).selectinload(ProduitAssurance.assureur_obj),
            selectinload(Sinistre.alerte).selectinload(Alerte.user),
        )
        .filter(Sinistre.id == sinistre_id)
        .first()
    )
