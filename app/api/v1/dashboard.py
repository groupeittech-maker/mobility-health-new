from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from decimal import Decimal
from app.core.database import get_db
from app.core.enums import Role, StatutSouscription, StatutPaiement
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.souscription import Souscription
from app.models.paiement import Paiement
from app.models.sinistre import Sinistre
from app.models.alerte import Alerte
from app.models.produit_assurance import ProduitAssurance
from app.models.hospital import Hospital
from pydantic import BaseModel
from typing import Dict


router = APIRouter()


def require_admin_or_backoffice(current_user: User = Depends(get_current_user)) -> User:
    """Dependency pour vérifier que l'utilisateur est admin ou a un rôle back-office"""
    allowed_roles = [Role.ADMIN, Role.DOCTOR, Role.FINANCE_MANAGER, Role.SOS_OPERATOR]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Back-office access required."
        )
    return current_user


class DashboardStatsResponse(BaseModel):
    """Statistiques du tableau de bord"""
    subscriptions_today: int
    subscriptions_pending: int
    sinistres_open: int
    payments_recent: List[dict]
    total_revenue: Decimal
    total_revenue_today: Decimal


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_backoffice)
):
    """Obtenir les statistiques du tableau de bord back-office"""
    
    # Date du jour (début et fin)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    # Nombre de souscriptions du jour
    subscriptions_today = db.query(Souscription).filter(
        and_(
            Souscription.created_at >= today_start,
            Souscription.created_at < today_end
        )
    ).count()
    
    # Souscriptions en attente de validation
    subscriptions_pending = db.query(Souscription).filter(
        Souscription.statut.in_([StatutSouscription.EN_ATTENTE, StatutSouscription.PENDING])
    ).count()
    
    # Sinistres ouverts (statut en_cours)
    sinistres_open = db.query(Sinistre).filter(
        Sinistre.statut == "en_cours"
    ).count()
    
    # Historique des paiements récents (30 derniers jours)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_payments = db.query(Paiement).filter(
        Paiement.created_at >= thirty_days_ago
    ).order_by(Paiement.created_at.desc()).limit(10).all()
    
    payments_recent = [
        {
            "id": p.id,
            "montant": float(p.montant),
            "statut": p.statut.value,
            "date_paiement": p.date_paiement.isoformat() if p.date_paiement else None,
            "created_at": p.created_at.isoformat(),
            "subscription_id": p.souscription_id,
            "user_id": p.user_id
        }
        for p in recent_payments
    ]
    
    # Revenus totaux (paiements validés)
    total_revenue_result = db.query(func.sum(Paiement.montant)).filter(
        Paiement.statut == StatutPaiement.VALIDE
    ).scalar()
    total_revenue = Decimal(total_revenue_result) if total_revenue_result else Decimal(0)
    
    # Revenus du jour
    revenue_today_result = db.query(func.sum(Paiement.montant)).filter(
        and_(
            Paiement.statut == StatutPaiement.VALIDE,
            Paiement.date_paiement >= today_start,
            Paiement.date_paiement < today_end
        )
    ).scalar()
    total_revenue_today = Decimal(revenue_today_result) if revenue_today_result else Decimal(0)
    
    return DashboardStatsResponse(
        subscriptions_today=subscriptions_today,
        subscriptions_pending=subscriptions_pending,
        sinistres_open=sinistres_open,
        payments_recent=payments_recent,
        total_revenue=total_revenue,
        total_revenue_today=total_revenue_today
    )


class StatisticsResponse(BaseModel):
    """Statistiques détaillées"""
    subscriptions_by_period: Dict[str, int]
    top_products: List[dict]
    revenue_by_period: Dict[str, float]
    sinistres_by_country: Dict[str, int]
    sinistres_by_product: Dict[str, int]


@router.get("/statistics", response_model=StatisticsResponse)
async def get_detailed_statistics(
    period: str = "month",  # "day", "week", "month", "year"
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_backoffice)
):
    """Obtenir les statistiques détaillées"""
    
    from datetime import datetime, timedelta
    from sqlalchemy import func, extract
    
    # Définir la période
    now = datetime.utcnow()
    if period == "day":
        start_date = now - timedelta(days=30)
        group_by = func.date(Souscription.created_at)
    elif period == "week":
        start_date = now - timedelta(weeks=12)
        group_by = func.date_trunc('week', Souscription.created_at)
    elif period == "month":
        start_date = now - timedelta(days=365)
        group_by = func.date_trunc('month', Souscription.created_at)
    else:  # year
        start_date = now - timedelta(days=365*5)
        group_by = func.date_trunc('year', Souscription.created_at)
    
    # Souscriptions par période
    subscriptions_by_period_query = db.query(
        group_by.label('period'),
        func.count(Souscription.id).label('count')
    ).filter(
        Souscription.created_at >= start_date
    ).group_by(group_by).order_by(group_by)
    
    subscriptions_by_period = {}
    for row in subscriptions_by_period_query.all():
        period_str = str(row.period) if row.period else "unknown"
        subscriptions_by_period[period_str] = row.count
    
    # Produits les plus vendus
    top_products_query = db.query(
        ProduitAssurance.nom,
        ProduitAssurance.id,
        func.count(Souscription.id).label('count')
    ).join(
        Souscription, Souscription.produit_assurance_id == ProduitAssurance.id
    ).filter(
        Souscription.created_at >= start_date
    ).group_by(
        ProduitAssurance.id, ProduitAssurance.nom
    ).order_by(
        func.count(Souscription.id).desc()
    ).limit(10)
    
    top_products = [
        {
            "id": row.id,
            "nom": row.nom,
            "count": row.count
        }
        for row in top_products_query.all()
    ]
    
    # Revenus par période
    revenue_by_period_query = db.query(
        group_by.label('period'),
        func.sum(Paiement.montant).label('total')
    ).join(
        Souscription, Paiement.souscription_id == Souscription.id
    ).filter(
        and_(
            Paiement.statut == StatutPaiement.VALIDE,
            Paiement.date_paiement >= start_date
        )
    ).group_by(group_by).order_by(group_by)
    
    revenue_by_period = {}
    for row in revenue_by_period_query.all():
        period_str = str(row.period) if row.period else "unknown"
        revenue_by_period[period_str] = float(row.total) if row.total else 0.0
    
    # Sinistres par pays (via les alertes)
    sinistres_by_country_query = db.query(
        func.coalesce(Alerte.adresse, 'Unknown').label('location'),
        func.count(Sinistre.id).label('count')
    ).join(
        Alerte, Sinistre.alerte_id == Alerte.id
    ).filter(
        Sinistre.created_at >= start_date
    ).group_by(Alerte.adresse)
    
    sinistres_by_country = {}
    for row in sinistres_by_country_query.all():
        # Extraire le pays de l'adresse si possible
        country = row.location.split(',')[-1].strip() if row.location and ',' in row.location else row.location or "Unknown"
        sinistres_by_country[country] = sinistres_by_country.get(country, 0) + row.count
    
    # Sinistres par produit
    sinistres_by_product_query = db.query(
        ProduitAssurance.nom,
        func.count(Sinistre.id).label('count')
    ).join(
        Souscription, Sinistre.souscription_id == Souscription.id
    ).join(
        ProduitAssurance, Souscription.produit_assurance_id == ProduitAssurance.id
    ).filter(
        Sinistre.created_at >= start_date
    ).group_by(ProduitAssurance.nom)
    
    sinistres_by_product = {
        row.nom: row.count
        for row in sinistres_by_product_query.all()
    }
    
    return StatisticsResponse(
        subscriptions_by_period=subscriptions_by_period,
        top_products=top_products,
        revenue_by_period=revenue_by_period,
        sinistres_by_country=sinistres_by_country,
        sinistres_by_product=sinistres_by_product
    )

