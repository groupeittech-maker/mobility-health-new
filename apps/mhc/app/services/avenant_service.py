"""Workflow des avenants de police : suspension, réémission, annulation.

Référentiel documentaire MHC (2ᵉ tableau) :
- Suspension : demandée par le souscripteur (MyMHC), motifs cochés + pièces
  justificatives (optionnel), puis validée par l'Assureur (rôle
  agent_sinistre_assureur). La validation suspend la police.
- Réémission : lève la suspension (reprise des garanties, échéance inchangée).
- Annulation : met fin définitivement à la police (déjà géré par ailleurs via
  la résiliation ; exposé ici pour cohérence de génération PDF).
"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.enums import StatutSouscription
from app.models.avenant import Avenant
from app.models.projet_voyage import ProjetVoyage
from app.models.souscription import Souscription
from app.models.user import User
from app.services.attestation_service import AttestationService
from app.services.mhc_reference_service import (
    allocate_avenant_reemission_number,
    allocate_avenant_suspension_number,
)
from app.services.official_travel_documents import (
    AVENANT_SUSPENSION_MOTIFS,
    AVENANT_SUSPENSION_PIECES,
    generate_avenant_reemission,
    generate_avenant_suspension,
)

TYPE_SUSPENSION = "suspension"
TYPE_REEMISSION = "reemission"
TYPE_ANNULATION = "annulation"

STATUT_DEMANDE = "demande"
STATUT_VALIDE = "valide"
STATUT_REFUSE = "refuse"
STATUT_EMIS = "emis"


class AvenantError(ValueError):
    """Erreur métier du workflow des avenants (→ HTTP 400)."""


def _statut_value(souscription: Souscription) -> str:
    statut = getattr(souscription, "statut", None)
    return getattr(statut, "value", statut)


def _traveler_and_minors(db: Session, souscription: Souscription):
    traveler_info = AttestationService._extract_traveler_info(db, souscription.id)
    minors_info = AttestationService._extract_minors_from_notes(souscription.notes or "")
    if not minors_info and souscription.projet_voyage_id:
        projet = db.query(ProjetVoyage).filter(ProjetVoyage.id == souscription.projet_voyage_id).first()
        if projet and getattr(projet, "notes", None):
            minors_info = AttestationService._extract_minors_from_notes(projet.notes)
    return traveler_info, minors_info


def _validate_keys(values: Optional[list], catalog: dict, label: str) -> list:
    values = [str(v) for v in (values or [])]
    unknown = [v for v in values if v not in catalog]
    if unknown:
        raise AvenantError(f"{label} inconnu(s) : {', '.join(unknown)}. Valeurs attendues : {', '.join(catalog)}.")
    return values


def request_suspension(
    db: Session,
    souscription: Souscription,
    actor: Optional[User],
    *,
    motifs: Optional[list] = None,
    motif_autre: Optional[str] = None,
    pieces: Optional[list] = None,
) -> Avenant:
    """Le souscripteur demande la suspension de sa police (en attente Assureur)."""
    statut = _statut_value(souscription)
    if statut == StatutSouscription.SUSPENDUE.value:
        raise AvenantError("La police est déjà suspendue.")
    if statut in {StatutSouscription.RESILIEE.value}:
        raise AvenantError("La police est résiliée : aucune suspension possible.")
    # Une demande de suspension déjà en attente ?
    existing = (
        db.query(Avenant)
        .filter(
            Avenant.souscription_id == souscription.id,
            Avenant.type_avenant == TYPE_SUSPENSION,
            Avenant.statut == STATUT_DEMANDE,
        )
        .first()
    )
    if existing:
        raise AvenantError("Une demande de suspension est déjà en attente de validation.")

    motifs = _validate_keys(motifs, AVENANT_SUSPENSION_MOTIFS, "Motif")
    if not motifs:
        raise AvenantError("Au moins un motif de suspension est requis.")
    if "autre" in motifs and not (motif_autre or "").strip():
        raise AvenantError("Le motif « Autre » nécessite une précision.")
    pieces = _validate_keys(pieces, AVENANT_SUSPENSION_PIECES, "Pièce justificative")

    numero = allocate_avenant_suspension_number(db)
    avenant = Avenant(
        souscription_id=souscription.id,
        type_avenant=TYPE_SUSPENSION,
        numero=numero,
        statut=STATUT_DEMANDE,
        motifs=motifs,
        motif_autre=(motif_autre or "").strip() or None,
        pieces_jointes=pieces,
        created_by_id=getattr(actor, "id", None),
    )
    db.add(avenant)
    db.flush()
    return avenant


def decide_suspension(
    db: Session,
    avenant: Avenant,
    actor: Optional[User],
    *,
    approve: bool,
    date_effet: Optional[datetime] = None,
    notes: Optional[str] = None,
) -> Avenant:
    """L'Assureur (agent_sinistre_assureur) valide ou refuse la suspension."""
    if avenant.type_avenant != TYPE_SUSPENSION:
        raise AvenantError("Cet avenant n'est pas une demande de suspension.")
    if avenant.statut != STATUT_DEMANDE:
        raise AvenantError("Cette demande de suspension a déjà été traitée.")

    avenant.decided_by_id = getattr(actor, "id", None)
    avenant.decided_at = datetime.utcnow()
    avenant.notes = notes
    if approve:
        avenant.decision_assureur = "approved"
        avenant.statut = STATUT_VALIDE
        avenant.date_effet = date_effet or datetime.utcnow()
        souscription = avenant.souscription or db.query(Souscription).filter(
            Souscription.id == avenant.souscription_id
        ).first()
        if souscription is not None:
            souscription.statut = StatutSouscription.SUSPENDUE
    else:
        avenant.decision_assureur = "rejected"
        avenant.statut = STATUT_REFUSE
    db.flush()
    return avenant


def issue_reemission(
    db: Session,
    souscription: Souscription,
    actor: Optional[User],
    *,
    date_effet: Optional[datetime] = None,
) -> Avenant:
    """Lève la suspension : réémission de la police (reprise des garanties)."""
    if _statut_value(souscription) != StatutSouscription.SUSPENDUE.value:
        raise AvenantError("La police n'est pas suspendue : aucune réémission possible.")

    parent = (
        db.query(Avenant)
        .filter(
            Avenant.souscription_id == souscription.id,
            Avenant.type_avenant == TYPE_SUSPENSION,
            Avenant.statut == STATUT_VALIDE,
        )
        .order_by(Avenant.created_at.desc())
        .first()
    )
    numero = allocate_avenant_reemission_number(db)
    avenant = Avenant(
        souscription_id=souscription.id,
        type_avenant=TYPE_REEMISSION,
        numero=numero,
        statut=STATUT_EMIS,
        date_effet=date_effet or datetime.utcnow(),
        date_echeance=getattr(souscription, "date_fin", None),
        parent_avenant_id=parent.id if parent else None,
        created_by_id=getattr(actor, "id", None),
    )
    db.add(avenant)
    souscription.statut = StatutSouscription.ACTIVE
    db.flush()
    return avenant


def build_avenant_pdf(db: Session, avenant: Avenant) -> BytesIO:
    """(Re)génère le PDF de l'avenant, toujours à jour avec l'état courant."""
    souscription = avenant.souscription or db.query(Souscription).filter(
        Souscription.id == avenant.souscription_id
    ).first()
    if souscription is None:
        raise AvenantError("Souscription introuvable pour cet avenant.")
    user = db.query(User).filter(User.id == souscription.user_id).first()
    traveler_info, minors_info = _traveler_and_minors(db, souscription)

    if avenant.type_avenant == TYPE_SUSPENSION:
        return generate_avenant_suspension(
            souscription,
            user,
            avenant.numero,
            traveler_info=traveler_info,
            minors_info=minors_info,
            motifs=avenant.motifs or [],
            motif_autre=avenant.motif_autre,
            pieces=avenant.pieces_jointes or [],
            decision=avenant.decision_assureur,
            date_effet=avenant.date_effet,
            date_emission=avenant.created_at,
        )
    if avenant.type_avenant == TYPE_REEMISSION:
        parent = None
        if avenant.parent_avenant_id:
            parent = db.query(Avenant).filter(Avenant.id == avenant.parent_avenant_id).first()
        return generate_avenant_reemission(
            souscription,
            user,
            avenant.numero,
            traveler_info=traveler_info,
            minors_info=minors_info,
            avenant_suspension_ref=parent.numero if parent else None,
            date_effet=avenant.date_effet,
            date_echeance=avenant.date_echeance,
            date_emission=avenant.created_at,
        )
    raise AvenantError(f"Type d'avenant non pris en charge : {avenant.type_avenant}")


def get_avenant(db: Session, avenant_id: int) -> Optional[Avenant]:
    return db.query(Avenant).filter(Avenant.id == avenant_id).first()


def list_avenants(db: Session, souscription_id: int) -> list[Avenant]:
    return (
        db.query(Avenant)
        .filter(Avenant.souscription_id == souscription_id)
        .order_by(Avenant.created_at.asc(), Avenant.id.asc())
        .all()
    )
