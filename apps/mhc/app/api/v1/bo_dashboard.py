"""Tableau de bord back-office — agrégats temps réel par profil."""
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.alerte import Alerte
from app.models.mhc_care_document import MhcCareDocument
from app.models.paiement import Paiement
from app.models.sinistre import Sinistre
from app.models.souscription import Souscription
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


def _role_str(u) -> str:
    r = getattr(u, "role", "user")
    return getattr(r, "value", r) or "user"


def _is_bo_role(role: str) -> bool:
    return role != "user"


def _count(db: Session, model, *filters) -> int:
    return db.query(func.count(model.id)).filter(*filters).scalar() or 0


def _month_start() -> datetime:
    now = datetime.utcnow()
    return datetime(now.year, now.month, 1)


@router.get("/dashboard/summary")
async def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """KPIs, répartitions et listes récentes — adaptées au profil connecté."""
    role = _role_str(current_user)
    if not _is_bo_role(role):
        raise HTTPException(status_code=403, detail="Espace réservé aux profils back-office")

    month_start = _month_start()
    stats = {}

    # ---- Alertes / demandes médicales ----
    stats["alertes"] = {
        "recues": _count(db, Alerte),
        "en_traitement": _count(db, Alerte, Alerte.statut.in_(["en_attente", "en_cours"])),
        "valides": _count(db, Alerte, Alerte.statut == "resolue"),
        "refusees": _count(db, Alerte, Alerte.statut == "annulee"),
        "cloturees": _count(db, Alerte, Alerte.statut == "cloturee"),
    }

    # Bons de prise en charge émis ce mois (par type).
    doc_rows = (
        db.query(MhcCareDocument.document_type, func.count(MhcCareDocument.id))
        .filter(MhcCareDocument.issued_at >= month_start)
        .group_by(MhcCareDocument.document_type)
        .all()
    )
    doc_counts = {str(t): c for t, c in doc_rows}
    stats["demandes_medicales"] = {
        "total_mois": sum(doc_counts.values()),
        "prises_en_charge_emises": doc_counts.get("bpcu", 0),
        "refus_emis": doc_counts.get("brpcu", 0),
        "hospitalisations": doc_counts.get("bh", 0),
        "prolongations": doc_counts.get("bph", 0),
        "rapatriements": doc_counts.get("brs", 0) + doc_counts.get("brf", 0),
        "bulletins_sortie": doc_counts.get("bs", 0),
    }

    # ---- Production ----
    primes = (
        db.query(func.coalesce(func.sum(Paiement.montant), 0))
        .filter(Paiement.statut == "valide", Paiement.created_at >= month_start)
        .scalar()
    )
    stats["production"] = {
        "comptes_crees": _count(db, User, User.created_at >= month_start),
        "souscriptions": _count(db, Souscription, Souscription.created_at >= month_start),
        "souscriptions_total": _count(db, Souscription),
        "primes_encaissees": float(primes or 0),
        "remboursements": _count(db, Paiement, Paiement.statut == "rembourse", Paiement.created_at >= month_start),
        "avenants": 0,
    }

    # ---- Sinistres ----
    stats["sinistres"] = {
        "total": _count(db, Sinistre),
        "en_cours": _count(db, Sinistre, Sinistre.statut == "en_cours"),
        "resolus": _count(db, Sinistre, Sinistre.statut == "resolu"),
        "annules": _count(db, Sinistre, Sinistre.statut == "annule"),
    }

    # ---- Répartition des demandes (types de bons, mois courant) ----
    stats["repartition_demandes"] = [
        {"label": "Prise en charge", "value": doc_counts.get("bpcu", 0), "color": "#4e267c"},
        {"label": "Hospitalisation", "value": doc_counts.get("bh", 0), "color": "#14AE98"},
        {"label": "Prolongation", "value": doc_counts.get("bph", 0), "color": "#2d5bd7"},
        {"label": "Rapatriement sanitaire", "value": doc_counts.get("brs", 0), "color": "#e8a13a"},
        {"label": "Rapatriement funéraire", "value": doc_counts.get("brf", 0), "color": "#8a5cf6"},
        {"label": "Rapport médical", "value": 0, "color": "#e23d3d"},
        {"label": "Facture hospitalière", "value": 0, "color": "#64748b"},
    ]
    total_docs = max(sum(doc_counts.values()), 1)

    # ---- Statut global des demandes (tous les documents du mois) ----
    validees = _count(db, MhcCareDocument, MhcCareDocument.validation_status == "valide")
    refusees = _count(db, MhcCareDocument, MhcCareDocument.validation_status == "refuse")
    en_attente_docs = _count(db, MhcCareDocument, MhcCareDocument.validation_status == "en_attente")
    stats["statut_global"] = {
        "validees": validees,
        "en_analyse": en_attente_docs,
        "refusees": refusees,
        "en_attente": stats["alertes"]["en_traitement"],
        "cloturees": stats["alertes"]["cloturees"],
    }

    # ---- Listes ----
    recent_subs: List[Souscription] = (
        db.query(Souscription).order_by(Souscription.created_at.desc()).limit(6).all()
    )
    stats["demandes_recentes"] = [
        {
            "numero": s.numero_souscription,
            "date": s.created_at.strftime("%d/%m/%Y %H:%M") if s.created_at else "",
            "assure": (s.user.full_name or s.user.username) if s.user else "—",
            "type": s.produit_assurance.nom if s.produit_assurance else "Souscription",
            "statut": str(getattr(s.statut, "value", s.statut)),
        }
        for s in recent_subs
    ]

    urgentes = (
        db.query(Alerte)
        .filter(Alerte.statut.in_(["en_attente", "en_cours"]))
        .order_by(Alerte.created_at.desc())
        .limit(5)
        .all()
    )
    stats["alertes_urgences"] = [
        {
            "id": a.id,
            "numero": a.numero_alerte,
            "date": a.created_at.strftime("%d/%m/%Y %H:%M") if a.created_at else "",
            "assure": (a.user.full_name or a.user.username) if a.user else "—",
            "motif": (a.description or "")[:60],
            "statut": a.statut,
            "priorite": a.priorite,
        }
        for a in urgentes
    ]

    # ---- Tâches à traiter ----
    stats["taches"] = {
        "comptes_en_attente": _count(db, User, User.validation_inscription == "pending"),
        "souscriptions_en_cours": _count(db, Souscription, Souscription.statut.in_(["en_attente", "en_attente_validation"])),
        "avenants": 0,
        "remboursements_a_valider": 0,
    }

    stats["role"] = role
    stats["generated_at"] = datetime.utcnow().isoformat()
    return stats
