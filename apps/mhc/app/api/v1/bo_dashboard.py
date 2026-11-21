"""Tableau de bord back-office — agrégats temps réel par profil."""
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.permissions import (
    F_ALERTE_SOS,
    F_BULLETIN_SORTIE,
    F_COMPTES_UTILISATEURS,
    F_FACTURATION_MEDICALE,
    F_HOSPITALISATION,
    F_PRISE_EN_CHARGE,
    F_PRODUCTION,
    F_RAPATRIEMENT,
    F_RAPPORT_MEDICAL,
    F_REMBOURSEMENT,
    F_SINISTRES,
    _FINANCE_FLOWS,
    has_permission,
)
from app.models.alerte import Alerte
from app.models.avenant import Avenant
from app.models.finance_refund import Refund
from app.models.invoice import Invoice
from app.models.mhc_care_document import MhcCareDocument
from app.models.paiement import Paiement
from app.models.rapport import Rapport
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

    # Périmètre effectif du profil — chaque bloc n'est émis que si la
    # fonctionnalité correspondante est consultable par le rôle.
    can_production = has_permission(role, F_PRODUCTION)
    can_sinistres = has_permission(role, F_SINISTRES)
    can_alertes = has_permission(role, F_ALERTE_SOS) or can_sinistres
    can_medical = any(
        has_permission(role, f)
        for f in (
            F_PRISE_EN_CHARGE,
            F_BULLETIN_SORTIE,
            F_HOSPITALISATION,
            F_RAPATRIEMENT,
            F_RAPPORT_MEDICAL,
            F_FACTURATION_MEDICALE,
        )
    )
    can_finance = any(has_permission(role, f) for f in _FINANCE_FLOWS)
    can_comptes = has_permission(role, F_COMPTES_UTILISATEURS)

    # ---- Alertes / demandes médicales ----
    if can_alertes:
        stats["alertes"] = {
            "recues": _count(db, Alerte),
            "en_traitement": _count(db, Alerte, Alerte.statut.in_(["en_attente", "en_cours"])),
            "valides": _count(db, Alerte, Alerte.statut == "resolue"),
            "refusees": _count(db, Alerte, Alerte.statut == "annulee"),
            "cloturees": _count(db, Alerte, Alerte.statut == "cloturee"),
        }

    if can_medical:
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
    else:
        doc_counts = {}

    if can_production or can_finance:
        primes = (
            db.query(func.coalesce(func.sum(Paiement.montant), 0))
            .filter(Paiement.statut == "valide", Paiement.created_at >= month_start)
            .scalar()
        )
    else:
        primes = 0

    if can_production:
        stats["production"] = {
            "comptes_crees": _count(db, User, User.created_at >= month_start),
            "souscriptions": _count(db, Souscription, Souscription.created_at >= month_start),
            "souscriptions_total": _count(db, Souscription),
            "primes_encaissees": float(primes or 0),
            "remboursements": _count(db, Paiement, Paiement.statut == "rembourse", Paiement.created_at >= month_start),
            "avenants": _count(db, Avenant, Avenant.created_at >= month_start),
        }

    if can_sinistres:
        stats["sinistres"] = {
            "total": _count(db, Sinistre),
            "en_cours": _count(db, Sinistre, Sinistre.statut == "en_cours"),
            "resolus": _count(db, Sinistre, Sinistre.statut == "resolu"),
            "annules": _count(db, Sinistre, Sinistre.statut == "annule"),
        }

    if can_finance:
        stats["finance"] = {
            "encaissements_attente": _count(db, Paiement, Paiement.statut == "en_attente"),
            "primes_mois": float(primes or 0),
            "remboursements_attente": _count(db, Refund, Refund.statut == "pending"),
            "factures_attente": _count(db, Invoice, Invoice.statut.like("pending%")),
            "paiements_mois": _count(db, Paiement, Paiement.created_at >= month_start),
        }

    if can_medical:
        # ---- Répartition des demandes (types de bons, mois courant) ----
        stats["repartition_demandes"] = [
            {"label": "Prise en charge", "value": doc_counts.get("bpcu", 0), "color": "#522880"},
            {"label": "Hospitalisation", "value": doc_counts.get("bh", 0), "color": "#1cad99"},
            {"label": "Prolongation", "value": doc_counts.get("bph", 0), "color": "#2f6fd6"},
            {"label": "Rapatriement sanitaire", "value": doc_counts.get("brs", 0), "color": "#d98a10"},
            {"label": "Rapatriement funéraire", "value": doc_counts.get("brf", 0), "color": "#8a63b5"},
            {"label": "Rapport médical", "value": _count(db, Rapport, Rapport.created_at >= month_start), "color": "#d64545"},
            {"label": "Facture hospitalière", "value": _count(db, Invoice, Invoice.created_at >= month_start), "color": "#7c7590"},
        ]

        # ---- Statut global des demandes (tous les documents du mois) ----
        stats["statut_global"] = {
            "validees": _count(db, MhcCareDocument, MhcCareDocument.validation_status == "valide"),
            "en_analyse": _count(db, MhcCareDocument, MhcCareDocument.validation_status == "en_attente"),
            "refusees": _count(db, MhcCareDocument, MhcCareDocument.validation_status == "refuse"),
            "en_attente": _count(db, Alerte, Alerte.statut.in_(["en_attente", "en_cours"])) if can_alertes else 0,
            "cloturees": _count(db, Alerte, Alerte.statut == "cloturee") if can_alertes else 0,
        }

    # ---- Listes (scopées par fonctionnalité) ----
    # « Demandes récentes » = dernières demandes médicales (bons MED-*), comme la maquette.
    if can_medical:
        from app.core.mhc_nomenclature import DOCUMENT_TITLES, MhcCareDocumentType

        recent_docs: List[MhcCareDocument] = (
            db.query(MhcCareDocument)
            .order_by(MhcCareDocument.issued_at.desc())
            .limit(6)
            .all()
        )

        def _doc_assure(doc: MhcCareDocument) -> str:
            payload = doc.payload or {}
            voyageur = payload.get("voyageur") or {}
            nom = voyageur.get("nom") or payload.get("assure") or payload.get("beneficiaire")
            if nom:
                return str(nom)
            sinistre = doc.sinistre
            if sinistre and sinistre.souscription and sinistre.souscription.user:
                u = sinistre.souscription.user
                return u.full_name or u.username or "—"
            return "—"

        stats["demandes_recentes"] = [
            {
                "numero": doc.numero,
                "date": doc.issued_at.strftime("%d/%m/%Y %H:%M") if doc.issued_at else "",
                "assure": _doc_assure(doc),
                "type": DOCUMENT_TITLES.get(MhcCareDocumentType(doc.document_type), doc.document_type)
                if doc.document_type in {t.value for t in MhcCareDocumentType} else doc.document_type,
                "statut": doc.validation_status or doc.statut,
            }
            for doc in recent_docs
        ]

    if can_alertes:
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

    # Listes par pôle : souscriptions et paiements récents (la vue demandes
    # médicales ci-dessus couvre les profils santé).
    if can_production:
        recent_subs = (
            db.query(Souscription)
            .order_by(Souscription.created_at.desc())
            .limit(6)
            .all()
        )
        stats["souscriptions_recentes"] = [
            {
                "id": s.id,
                "numero": s.numero_souscription or f"SUB-{s.id}",
                "date": s.created_at.strftime("%d/%m/%Y %H:%M") if s.created_at else "",
                "assure": (s.user.full_name or s.user.username) if s.user else "—",
                "prix": float(s.prix_applique or 0),
                "statut": str(s.statut.value if hasattr(s.statut, "value") else s.statut),
            }
            for s in recent_subs
        ]

    if can_finance:
        recent_pay = (
            db.query(Paiement)
            .order_by(Paiement.created_at.desc())
            .limit(6)
            .all()
        )
        stats["paiements_recents"] = [
            {
                "id": p.id,
                "reference": f"PAY-{p.id}",
                "date": p.created_at.strftime("%d/%m/%Y %H:%M") if p.created_at else "",
                "montant": float(p.montant or 0),
                "statut": str(p.statut.value if hasattr(p.statut, "value") else p.statut),
                "souscription_id": p.souscription_id,
            }
            for p in recent_pay
        ]

    # ---- Tâches à traiter (clés émises selon la fonctionnalité) ----
    taches = {}
    if can_comptes:
        taches["comptes_en_attente"] = _count(db, User, User.validation_inscription == "pending")
    if can_production:
        taches["souscriptions_en_cours"] = _count(db, Souscription, Souscription.statut.in_(["en_attente", "en_attente_validation"]))
        taches["avenants"] = _count(db, Avenant, Avenant.statut == "demande")
    if has_permission(role, F_REMBOURSEMENT):
        taches["remboursements_a_valider"] = _count(db, Refund, Refund.statut == "pending")
    stats["taches"] = taches

    stats["role"] = role
    stats["generated_at"] = datetime.utcnow().isoformat()
    return stats
