from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.enums import Role
from app.models.user import User
from app.services.statistics_service import StatisticsService

router = APIRouter()


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role not in (Role.ADMIN.value, Role.FINANCE_MANAGER.value, Role.AGENT_COMPTABLE_MH.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs et agents comptables.",
        )
    return current_user


def _common_params(
    start_date: Optional[date] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    produit_id: Optional[int] = Query(None, description="ID du produit d'assurance"),
    assureur_id: Optional[int] = Query(None, description="ID de l'assureur"),
    courtier_id: Optional[int] = Query(None, description="ID du courtier"),
    pays: Optional[str] = Query(None, description="Pays"),
    canal: Optional[str] = Query(None, description="Canal de distribution (assureur/courtier)"),
    group_by: Optional[str] = Query(None, description="Groupe temporel (day, week, month, quarter, year)"),
):
    return {
        "start_date": start_date,
        "end_date": end_date,
        "produit_id": produit_id,
        "assureur_id": assureur_id,
        "courtier_id": courtier_id,
        "pays": pays,
        "canal": canal,
        "group_by": group_by,
    }


@router.get("", summary="Rapport statistique complet")
async def full_statistics(
    params: dict = Depends(_common_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    """Retourne l'ensemble des statistiques dans un seul endpoint."""
    return StatisticsService.full_report(db, **params)


@router.get("/overview", summary="Vue d'ensemble (KPIs)")
async def overview_statistics(
    params: dict = Depends(_common_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    return StatisticsService.overview(db, **params)


@router.get("/subscriptions", summary="Statistiques des souscriptions")
async def subscriptions_statistics(
    params: dict = Depends(_common_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    return StatisticsService.subscriptions(db, **params)


@router.get("/payments", summary="Statistiques des paiements")
async def payments_statistics(
    params: dict = Depends(_common_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    return StatisticsService.payments(db, **params)


@router.get("/claims", summary="Statistiques des sinistres")
async def claims_statistics(
    params: dict = Depends(_common_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    return StatisticsService.claims(db, **params)


@router.get("/reviews", summary="Statistiques du pipeline de validation")
async def reviews_statistics(
    params: dict = Depends(_common_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    return StatisticsService.reviews(db, **params)


@router.get("/finance", summary="Statistiques financières")
async def finance_statistics(
    params: dict = Depends(_common_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    return StatisticsService.finance(db, **params)


@router.get("/users", summary="Statistiques des utilisateurs")
async def users_statistics(
    start_date: Optional[date] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    pays: Optional[str] = Query(None, description="Pays"),
    group_by: Optional[str] = Query(None, description="Groupe temporel"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    return StatisticsService.users(db, start_date, end_date, group_by, pays)


@router.get("/products", summary="Statistiques produits et destinations")
async def products_statistics(
    params: dict = Depends(_common_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    return StatisticsService.products(db, **params)


@router.get("/ekyc", summary="Statistiques eKYC")
async def ekyc_statistics(
    start_date: Optional[date] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    return StatisticsService.ekyc(db, start_date, end_date)
