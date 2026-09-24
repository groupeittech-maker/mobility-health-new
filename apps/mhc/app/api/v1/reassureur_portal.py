"""Portail réassureur — consultation production, sinistres, encaissements, quote-parts."""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.permissions import (
    F_ENCAISSEMENT_QUOTE_PART_SINISTRE,
    LEVEL_CONSULTATION,
    has_permission,
)
from app.models.finance_outbound import PaiementFournisseur
from app.models.paiement import Paiement
from app.models.produit_assurance import ProduitAssurance
from app.models.reassureur import Reassureur
from app.models.sinistre import Sinistre
from app.models.souscription import Souscription
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


def _role_str(u) -> str:
    r = getattr(u, "role", "user")
    return getattr(r, "value", r) or "user"


def _resolve_reassureur_id(current_user, requested: Optional[int], db: Session) -> int:
    role = _role_str(current_user)
    if role == "admin" or getattr(current_user, "is_superuser", False):
        if requested:
            return requested
        first = db.query(Reassureur).filter(Reassureur.est_actif == True).first()
        if first:
            return first.id
        raise HTTPException(status_code=404, detail="Aucun réassureur actif")
    rid = getattr(current_user, "reassureur_id", None)
    if not rid:
        raise HTTPException(status_code=403, detail="Compte non rattaché à un réassureur")
    if requested and requested != rid:
        raise HTTPException(status_code=403, detail="Accès limité à votre réassureur")
    return rid


def _product_ids(db: Session, reassureur_id: int) -> List[int]:
    return [p.id for p in db.query(ProduitAssurance.id).filter(ProduitAssurance.reassureur_id == reassureur_id).all()]


@router.get("/overview")
async def reassureur_overview(
    reassureur_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Vue consolidée : produits cédés, production, sinistres, encaissements, quote-parts."""
    role = _role_str(current_user)
    if not (
        role in ("admin", "agent_verificateur_reassureur", "superviseur_technique", "superviseur_comptable")
        or getattr(current_user, "is_superuser", False)
        or has_permission(role, F_ENCAISSEMENT_QUOTE_PART_SINISTRE, LEVEL_CONSULTATION)
    ):
        raise HTTPException(status_code=403, detail="Accès réservé au réassureur / contrôle")

    rid = _resolve_reassureur_id(current_user, reassureur_id, db)
    reassureur = db.query(Reassureur).filter(Reassureur.id == rid).first()
    if not reassureur:
        raise HTTPException(status_code=404, detail="Réassureur introuvable")
    pids = _product_ids(db, rid)

    produits = db.query(ProduitAssurance).filter(ProduitAssurance.reassureur_id == rid).all()
    souscriptions = (
        db.query(Souscription).filter(Souscription.produit_assurance_id.in_(pids)).all() if pids else []
    )
    sub_ids = [s.id for s in souscriptions]
    sinistres = (
        db.query(Sinistre).filter(Sinistre.souscription_id.in_(sub_ids)).all() if sub_ids else []
    )
    paiements = (
        db.query(Paiement).filter(Paiement.souscription_id.in_(sub_ids), Paiement.statut == "valide").all()
        if sub_ids else []
    )
    quote_parts = (
        db.query(PaiementFournisseur)
        .filter(
            PaiementFournisseur.type_paiement == "quote_part_sinistre_reassureur",
            PaiementFournisseur.beneficiaire_id == rid,
        )
        .all()
    )

    return {
        "reassureur": {"id": reassureur.id, "nom": reassureur.nom, "code": reassureur.code, "pays": reassureur.pays},
        "produits": [{"id": p.id, "nom": p.nom, "code": p.code, "cession_pct": float(p.cession_reassureur_pct or 0)} for p in produits],
        "production": {
            "nb_souscriptions": len(souscriptions),
            "actives": sum(1 for s in souscriptions if str(getattr(s.statut, "value", s.statut)) == "active"),
            "items": [
                {
                    "id": s.id,
                    "numero": s.numero_souscription,
                    "statut": str(getattr(s.statut, "value", s.statut)),
                    "prix_applique": float(s.prix_applique or 0),
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in souscriptions[:200]
            ],
        },
        "sinistres": {
            "total": len(sinistres),
            "items": [
                {
                    "id": s.id,
                    "numero": s.numero_sinistre,
                    "statut": str(getattr(s.statut, "value", s.statut)),
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in sinistres[:200]
            ],
        },
        "encaissements": {
            "total": len(paiements),
            "montant_total": sum(float(p.montant or 0) for p in paiements),
        },
        "quote_parts": [
            {
                "id": p.id,
                "reference": p.reference,
                "montant": float(p.montant),
                "devise": p.devise,
                "statut": p.statut,
                "periode": p.periode,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in quote_parts
        ],
    }
