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
from app.services.mhc_reference_service import allocate_document_number

CLOSING_TYPES = {
    MhcCareDocumentType.BRPCU,
    MhcCareDocumentType.ARS,
    MhcCareDocumentType.ARF,
}


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


def _inject_certificat_deces(actions: List[str], docs: Iterable[MhcCareDocument]) -> List[str]:
    """Propose le certificat de décès dans la branche funéraire (téléchargement par le médecin traitant)."""
    if _has_type(docs, MhcCareDocumentType.CERTIFICAT_DECES):
        return actions
    if not actions:
        return actions
    if MhcCareDocumentType.BRF.value in actions or MhcCareDocumentType.ARF.value in actions:
        return [MhcCareDocumentType.CERTIFICAT_DECES.value] + actions
    return actions


def allowed_next_actions(sinistre: Sinistre) -> List[str]:
    docs = _docs(sinistre)
    for doc in docs:
        _expire_if_needed(doc)

    if _has_type(docs, MhcCareDocumentType.ARF):
        return _inject_certificat_deces([], docs)
    if _has_type(docs, MhcCareDocumentType.ARS):
        return _inject_certificat_deces([], docs)
    if _has_type(docs, MhcCareDocumentType.BRPCU):
        return _inject_certificat_deces([], docs)
    if _has_type(docs, MhcCareDocumentType.BRF):
        return _inject_certificat_deces([MhcCareDocumentType.ARF.value], docs)
    if _has_type(docs, MhcCareDocumentType.BRS) and not _has_type(docs, MhcCareDocumentType.ARS):
        return _inject_certificat_deces(
            [MhcCareDocumentType.ARS.value, MhcCareDocumentType.BRF.value],
            docs,
        )

    if _has_type(docs, MhcCareDocumentType.BS):
        bs = _latest(docs, MhcCareDocumentType.BS)
        mode = (bs.payload or {}).get("mode_sortie") if bs else None
        if mode == MhcExitMode.RAPATRIEMENT_SANITAIRE.value and not _has_type(docs, MhcCareDocumentType.BRS):
            return _inject_certificat_deces(
                [MhcCareDocumentType.BRS.value, MhcCareDocumentType.BRF.value],
                docs,
            )
        actions = [MhcCareDocumentType.BRF.value] if not _dossier_closed(docs) else []
        return _inject_certificat_deces(actions, docs)

    if _has_type(docs, MhcCareDocumentType.BPH) or _has_type(docs, MhcCareDocumentType.BH):
        return _inject_certificat_deces(
            [
                MhcCareDocumentType.BPH.value,
                MhcCareDocumentType.BS.value,
                MhcCareDocumentType.BRF.value,
            ],
            docs,
        )
    if _has_type(docs, MhcCareDocumentType.BPCU):
        return _inject_certificat_deces(
            [
                MhcCareDocumentType.BH.value,
                MhcCareDocumentType.BS.value,
                MhcCareDocumentType.BRF.value,
            ],
            docs,
        )
    if sinistre.numero_sinistre:
        return _inject_certificat_deces(
            [MhcCareDocumentType.BPCU.value, MhcCareDocumentType.BRPCU.value, MhcCareDocumentType.BRF.value],
            docs,
        )
    return _inject_certificat_deces(
        [MhcCareDocumentType.BPCU.value, MhcCareDocumentType.BRPCU.value, MhcCareDocumentType.BRF.value],
        docs,
    )


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
) -> List[MhcCareDocument]:
    doc_type = _as_type(document_type)
    payload = dict(payload or {})
    alerte = alerte or getattr(sinistre, "alerte", None)

    if not sinistre.numero_sinistre and doc_type not in {
        MhcCareDocumentType.BRF,
        MhcCareDocumentType.CERTIFICAT_DECES,
    }:
        raise ValueError("Le numéro de sinistre doit être attribué avant l'émission d'un bon.")

    created: List[MhcCareDocument] = []

    if doc_type == MhcCareDocumentType.BS:
        mode = payload.get("mode_sortie") or MhcExitMode.GUERISON.value
        payload["mode_sortie"] = mode
        _require_allowed(sinistre, MhcCareDocumentType.BS)
        bulletin = _create_document(db, sinistre, MhcCareDocumentType.BS, actor, payload, notes=notes)
        created.append(bulletin)
        if mode == MhcExitMode.RAPATRIEMENT_SANITAIRE.value:
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
            _close_dossier(sinistre, alerte)
        return created

    _require_allowed(sinistre, doc_type)
    document = _create_document(db, sinistre, doc_type, actor, payload, notes=notes)
    created.append(document)

    if doc_type in CLOSING_TYPES:
        if doc_type == MhcCareDocumentType.BRPCU:
            sinistre.statut = "annule"
            if alerte:
                alerte.statut = "annulee"
        else:
            _close_dossier(sinistre, alerte)
    return created


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
    return issue_care_document(
        db,
        sinistre,
        doc_type.value,
        actor,
        payload=payload,
        notes=notes,
        alerte=alerte,
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
