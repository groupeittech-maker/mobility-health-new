"""Paiements sortants et rapprochement encaissements ↔ polices émises."""
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.permissions import (
    F_PAIEMENT_SINISTRE,
    LEVEL_CONSULTATION,
    LEVEL_CONTROLE,
    LEVEL_EDITION,
    has_permission,
)
from app.models.finance_outbound import PaiementFournisseur
from app.models.paiement import Paiement
from app.models.souscription import Souscription
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

TYPE_TO_FEATURE = {
    "cession_reassurance": "paiement_cession_reassurance",
    "retention_assureur": "paiement_retention_assureur",
    "commission_cession": "paiement_commission_cession",
    "commission_courtage": "paiement_commission_courtage",
    "cout_police": "paiement_cout_police",
    "taxe": "paiement_taxe",
    "taxe_additionnelle": "paiement_taxe_additionnelle",
    "retrocession_mhc": "retrocession_mhc",
    "quote_part_sinistre_reassureur": "paiement_sinistre",
    "facture_hopital": "paiement_facture_hopital",
}


def _role_str(u) -> str:
    r = getattr(u, "role", "user")
    return getattr(r, "value", r) or "user"


def _check(u, type_paiement: str, level: str) -> None:
    feature = TYPE_TO_FEATURE.get(type_paiement, F_PAIEMENT_SINISTRE)
    if not has_permission(_role_str(u), feature, level):
        raise HTTPException(status_code=403, detail=f"Permission « {feature} » ({level}) requise")


class OutboundCreate(BaseModel):
    type_paiement: str
    beneficiaire_type: str
    beneficiaire_id: Optional[int] = None
    beneficiaire_nom: Optional[str] = None
    montant: float
    devise: str = "XAF"
    periode: Optional[str] = None
    sinistre_id: Optional[int] = None
    souscription_id: Optional[int] = None
    produit_id: Optional[int] = None
    description: Optional[str] = None


def _to_dict(p: PaiementFournisseur) -> dict:
    return {
        "id": p.id,
        "reference": p.reference,
        "type_paiement": p.type_paiement,
        "beneficiaire_type": p.beneficiaire_type,
        "beneficiaire_id": p.beneficiaire_id,
        "beneficiaire_nom": p.beneficiaire_nom,
        "montant": float(p.montant),
        "devise": p.devise,
        "periode": p.periode,
        "sinistre_id": p.sinistre_id,
        "souscription_id": p.souscription_id,
        "statut": p.statut,
        "description": p.description,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "controlled_at": p.controlled_at.isoformat() if p.controlled_at else None,
        "paid_at": p.paid_at.isoformat() if p.paid_at else None,
    }


@router.get("/outbound", response_model=List[dict])
async def list_outbound(
    type_paiement: Optional[str] = None,
    statut: Optional[str] = None,
    periode: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Lecture : consultation sur n'importe quel flux de paiement.
    allowed = {t for t, f in TYPE_TO_FEATURE.items() if has_permission(_role_str(current_user), f, LEVEL_CONSULTATION)}
    if _role_str(current_user) == "admin":
        allowed = set(TYPE_TO_FEATURE)
    if not allowed:
        raise HTTPException(status_code=403, detail="Aucun flux de paiement consultable")
    q = db.query(PaiementFournisseur).filter(PaiementFournisseur.type_paiement.in_(allowed))
    if type_paiement:
        if type_paiement not in allowed:
            raise HTTPException(status_code=403, detail="Flux non autorisé")
        q = q.filter(PaiementFournisseur.type_paiement == type_paiement)
    if statut:
        q = q.filter(PaiementFournisseur.statut == statut)
    if periode:
        q = q.filter(PaiementFournisseur.periode == periode)
    return [_to_dict(p) for p in q.order_by(PaiementFournisseur.created_at.desc()).limit(500).all()]


@router.post("/outbound", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_outbound(
    payload: OutboundCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.type_paiement not in PaiementFournisseur.TYPES:
        raise HTTPException(status_code=400, detail=f"type_paiement invalide : {sorted(PaiementFournisseur.TYPES)}")
    _check(current_user, payload.type_paiement, LEVEL_EDITION)
    p = PaiementFournisseur(
        reference=f"PF-{datetime.utcnow().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}",
        type_paiement=payload.type_paiement,
        beneficiaire_type=payload.beneficiaire_type,
        beneficiaire_id=payload.beneficiaire_id,
        beneficiaire_nom=payload.beneficiaire_nom,
        montant=payload.montant,
        devise=payload.devise,
        periode=payload.periode,
        sinistre_id=payload.sinistre_id,
        souscription_id=payload.souscription_id,
        produit_id=payload.produit_id,
        description=payload.description,
        created_by_id=current_user.id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _to_dict(p)


@router.post("/outbound/{payment_id}/control")
async def control_outbound(payment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = db.query(PaiementFournisseur).filter(PaiementFournisseur.id == payment_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Paiement introuvable")
    if p.statut != "a_payer":
        raise HTTPException(status_code=400, detail=f"Statut actuel : {p.statut}")
    _check(current_user, p.type_paiement, LEVEL_CONTROLE)
    p.statut = "controle"
    p.controlled_by_id = current_user.id
    p.controlled_at = datetime.utcnow()
    db.commit()
    return _to_dict(p)


@router.post("/outbound/{payment_id}/pay")
async def pay_outbound(payment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = db.query(PaiementFournisseur).filter(PaiementFournisseur.id == payment_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Paiement introuvable")
    if p.statut not in ("a_payer", "controle"):
        raise HTTPException(status_code=400, detail=f"Statut actuel : {p.statut}")
    _check(current_user, p.type_paiement, LEVEL_EDITION)
    p.statut = "paye"
    p.paid_by_id = current_user.id
    p.paid_at = datetime.utcnow()
    db.commit()
    return _to_dict(p)


@router.post("/outbound/{payment_id}/cancel")
async def cancel_outbound(payment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = db.query(PaiementFournisseur).filter(PaiementFournisseur.id == payment_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Paiement introuvable")
    if p.statut == "paye":
        raise HTTPException(status_code=400, detail="Un paiement effectué ne peut être annulé")
    _check(current_user, p.type_paiement, LEVEL_EDITION)
    p.statut = "annule"
    db.commit()
    return _to_dict(p)


@router.get("/reconciliation")
async def reconciliation(
    periode: Optional[str] = Query(None, description="Format AAAA-MM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rapprochement : polices émises (souscriptions validées/payées) ↔ primes encaissées."""
    if not has_permission(_role_str(current_user), "encaissement_prime", LEVEL_CONSULTATION):
        raise HTTPException(status_code=403, detail="Permission encaissement_prime requise")

    souscriptions_q = db.query(Souscription).filter(Souscription.statut.in_(["active", "en_attente_paiement", "expiree"]))
    if periode:
        try:
            y, m = int(periode[:4]), int(periode[5:7])
            start = datetime(y, m, 1)
            end = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)
            souscriptions_q = souscriptions_q.filter(Souscription.created_at >= start, Souscription.created_at < end)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="periode attendue au format AAAA-MM")
    souscriptions = souscriptions_q.all()

    paid_sub_ids = set()
    for row in db.query(Paiement.souscription_id).filter(Paiement.statut == "valide").all():
        paid_sub_ids.add(row[0])

    ecarts = []
    total_attendu = 0.0
    total_encaisse = 0.0
    for s in souscriptions:
        attendu = float(s.prix_applique or 0)
        paye = s.id in paid_sub_ids
        total_attendu += attendu
        if paye:
            total_encaisse += attendu
        else:
            ecarts.append({
                "souscription_id": s.id,
                "numero_souscription": s.numero_souscription,
                "statut": s.statut,
                "montant_attendu": attendu,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            })
    return {
        "periode": periode,
        "polices_emises": len(souscriptions),
        "polices_reglees": len(paid_sub_ids),
        "total_attendu": total_attendu,
        "total_encaisse": total_encaisse,
        "ecart": total_attendu - total_encaisse,
        "dossiers_non_regles": ecarts[:200],
    }
