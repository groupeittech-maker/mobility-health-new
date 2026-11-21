from datetime import date, timedelta
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.enums import Role
from app.core.permissions import require_backoffice
from app.models.user import User
from app.services.statistics_service import StatisticsService

router = APIRouter()


def _resolve_period(period: Optional[str]) -> Tuple[Optional[date], Optional[date]]:
    """Convertit une période prédéfinie en dates de début/fin."""
    if not period or period == "all":
        return None, None

    today = date.today()

    if period == "month":
        return today.replace(day=1), today

    if period == "last_month":
        first_of_month = today.replace(day=1)
        last_of_previous = first_of_month - timedelta(days=1)
        first_of_previous = last_of_previous.replace(day=1)
        return first_of_previous, last_of_previous

    if period == "quarter":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        return today.replace(month=quarter_start_month, day=1), today

    if period == "year":
        return today.replace(month=1, day=1), today

    if period == "week":
        return today - timedelta(days=today.weekday()), today

    # 'custom' ou valeur inconnue : conserver les dates explicites
    return None, None


def _common_params(
    start_date: Optional[date] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    period: Optional[str] = Query(None, description="Période prédéfinie (all, week, month, last_month, quarter, year, custom)"),
    produit_id: Optional[int] = Query(None, description="ID du produit d'assurance"),
    assureur_id: Optional[int] = Query(None, description="ID de l'assureur"),
    courtier_id: Optional[int] = Query(None, description="ID du courtier"),
    pays: Optional[str] = Query(None, description="Pays"),
    canal: Optional[str] = Query(None, description="Canal de distribution (assureur/courtier)"),
    group_by: Optional[str] = Query(None, description="Groupe temporel (day, week, month, quarter, year)"),
):
    if period and period != "custom":
        resolved_start, resolved_end = _resolve_period(period)
        start_date, end_date = resolved_start, resolved_end

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
    current_user: User = Depends(require_backoffice()),
):
    """Retourne l'ensemble des statistiques dans un seul endpoint."""
    return StatisticsService.full_report(db, **params)


@router.get("/overview", summary="Vue d'ensemble (KPIs)")
async def overview_statistics(
    params: dict = Depends(_common_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_backoffice()),
):
    return StatisticsService.overview(db, **params)


@router.get("/subscriptions", summary="Statistiques des souscriptions")
async def subscriptions_statistics(
    params: dict = Depends(_common_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_backoffice()),
):
    return StatisticsService.subscriptions(db, **params)


@router.get("/payments", summary="Statistiques des paiements")
async def payments_statistics(
    params: dict = Depends(_common_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_backoffice()),
):
    return StatisticsService.payments(db, **params)


@router.get("/claims", summary="Statistiques des sinistres")
async def claims_statistics(
    params: dict = Depends(_common_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_backoffice()),
):
    return StatisticsService.claims(db, **params)


@router.get("/reviews", summary="Statistiques du pipeline de validation")
async def reviews_statistics(
    params: dict = Depends(_common_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_backoffice()),
):
    return StatisticsService.reviews(db, **params)


@router.get("/finance", summary="Statistiques financières")
async def finance_statistics(
    params: dict = Depends(_common_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_backoffice()),
):
    return StatisticsService.finance(db, **params)


@router.get("/users", summary="Statistiques des utilisateurs")
async def users_statistics(
    start_date: Optional[date] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    period: Optional[str] = Query(None, description="Période prédéfinie"),
    pays: Optional[str] = Query(None, description="Pays"),
    group_by: Optional[str] = Query(None, description="Groupe temporel"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_backoffice()),
):
    if period and period != "custom":
        start_date, end_date = _resolve_period(period)
    return StatisticsService.users(db, start_date, end_date, group_by, pays)


@router.get("/products", summary="Statistiques produits et destinations")
async def products_statistics(
    params: dict = Depends(_common_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_backoffice()),
):
    return StatisticsService.products(db, **params)


@router.get("/ekyc", summary="Statistiques eKYC")
async def ekyc_statistics(
    start_date: Optional[date] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    period: Optional[str] = Query(None, description="Période prédéfinie"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_backoffice()),
):
    if period and period != "custom":
        start_date, end_date = _resolve_period(period)
    return StatisticsService.ekyc(db, start_date, end_date)


@router.get("/nav-counts", summary="Compteurs en attente pour les badges de navigation")
async def nav_counts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_backoffice()),
):
    """Compteurs légers des files de travail en attente — alimente les badges
    de la sidebar back-office (un appel, mis en cache côté client)."""
    from sqlalchemy import func
    from app.models.souscription import Souscription
    from app.models.avenant import Avenant
    from app.models.reclamation import Reclamation
    from app.models.alerte import Alerte
    from app.models.invoice import Invoice
    from app.models.ristourne import Ristourne
    from app.models.profile_change import ProfileChangeRequest
    from app.models.paiement import Paiement
    from app.models.medical_workflow import HospitalMedicalReport
    from sqlalchemy import text as _text

    def n(query) -> int:
        return int(query.scalar() or 0)

    return {
        "inscriptions_attente": n(db.query(func.count(User.id)).filter(
            User.validation_inscription == "pending",
            _text("LOWER(CAST(users.role AS TEXT)) = 'user'"),
        )),
        "profils_attente": n(db.query(func.count(ProfileChangeRequest.id)).filter(
            ProfileChangeRequest.statut == "pending")),
        "souscriptions_attente": n(db.query(func.count(Souscription.id)).filter(
            Souscription.statut == "en_attente_validation")),
        "avenants_en_cours": n(db.query(func.count(Avenant.id)).filter(
            Avenant.statut.like("attente%"))),
        "reclamations_ouvertes": n(db.query(func.count(Reclamation.id)).filter(
            Reclamation.statut.in_(["recue", "en_cours"]))),
        "alertes_actives": n(db.query(func.count(Alerte.id)).filter(
            Alerte.statut.in_(["en_attente", "en_cours"]))),
        "validations_medicales": n(db.query(func.count(HospitalMedicalReport.id)).filter(
            HospitalMedicalReport.statut.in_(["soumis", "validee_mc"]))),
        "factures_attente": n(db.query(func.count(Invoice.id)).filter(
            Invoice.statut.like("pending%"))),
        "remboursements_attente": n(db.query(func.count(Ristourne.id)).filter(
            Ristourne.statut == "a_rembourser")),
        "encaissements_attente": n(db.query(func.count(Paiement.id)).filter(
            Paiement.statut == "en_attente")),
    }


# ---------------------------------------------------------------------------
# Recherche globale back-office + journal des actions (UX transverse)
# ---------------------------------------------------------------------------

@router.get("/search")
async def admin_global_search(
    q: str = Query(..., min_length=2, max_length=80),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_backoffice()),
):
    """Recherche transverse : souscriptions, alertes, assurés, factures."""
    from sqlalchemy import or_
    from app.models.alerte import Alerte
    from app.models.invoice import Invoice
    from app.models.souscription import Souscription

    term = f"%{q.strip()}%"
    results = []

    subs = (
        db.query(Souscription, User)
        .join(User, Souscription.user_id == User.id)
        .filter(or_(
            Souscription.numero_souscription.ilike(term),
            User.full_name.ilike(term),
        ))
        .order_by(Souscription.created_at.desc())
        .limit(8)
        .all()
    )
    for s, u in subs:
        results.append({
            "type": "souscription", "id": s.id,
            "numero": s.numero_souscription or f"SUB-{s.id}",
            "label": u.full_name or u.username or "—",
            "sub": str(s.statut.value if hasattr(s.statut, "value") else s.statut),
            "href": "admin-subscriptions.html",
        })

    alertes = (
        db.query(Alerte, User)
        .join(User, Alerte.user_id == User.id)
        .filter(or_(
            Alerte.numero_alerte.ilike(term),
            User.full_name.ilike(term),
        ))
        .order_by(Alerte.created_at.desc())
        .limit(8)
        .all()
    )
    for a, u in alertes:
        results.append({
            "type": "alerte", "id": a.id,
            "numero": a.numero_alerte or f"URG-{a.id}",
            "label": u.full_name or u.username or "—",
            "sub": a.statut,
            "href": f"alert-center.html?focus={a.id}",
        })

    assures = (
        db.query(User)
        .filter(User.role == Role.USER, or_(
            User.full_name.ilike(term),
            User.email.ilike(term),
            User.username.ilike(term),
        ))
        .order_by(User.created_at.desc())
        .limit(8)
        .all()
    )
    for u in assures:
        results.append({
            "type": "assure", "id": u.id,
            "numero": None,
            "label": u.full_name or u.username or "—",
            "sub": u.email or "",
            "href": "admin-users.html?role=user",
        })

    factures = (
        db.query(Invoice)
        .filter(Invoice.numero_facture.ilike(term))
        .order_by(Invoice.created_at.desc())
        .limit(8)
        .all()
    )
    for f in factures:
        results.append({
            "type": "facture", "id": f.id,
            "numero": f.numero_facture,
            "label": "Facture hospitalière",
            "sub": str(f.statut.value if hasattr(f.statut, "value") else f.statut),
            "href": "sinistre-invoices.html",
        })

    return {"results": results[:24]}


_JOURNAL_ROLES = {
    Role.ADMIN, Role.SUPERVISEUR_TECHNIQUE, Role.SUPERVISEUR_COMPTABLE,
    Role.SUPERVISEUR_AFFAIRES_MEDICALES,
    Role.AGENT_CONFORMITE_PRODUCTION, Role.AGENT_CONFORMITE_SINISTRE,
    Role.AGENT_CONFORMITE_MEDICAL, Role.AGENT_CONFORMITE_COMPTABLE,
}


@router.get("/audit-journal")
async def admin_audit_journal(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    method: Optional[str] = None,
    path: Optional[str] = None,
    status_code: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_backoffice()),
):
    """Journal des actions (audit API) — lecture seule, corps exclus."""
    if current_user.role not in _JOURNAL_ROLES:
        raise HTTPException(status_code=403, detail="Journal réservé à la direction et à la conformité")
    from app.models.audit import AuditLog

    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    if method:
        query = query.filter(AuditLog.method == method.upper())
    if path:
        query = query.filter(AuditLog.path.ilike(f"%{path}%"))
    if status_code is not None:
        query = query.filter(AuditLog.status_code == status_code)

    rows = query.offset(skip).limit(limit).all()
    user_ids = {r.user_id for r in rows if r.user_id}
    names = {
        u.id: (u.full_name or u.username or f"#{u.id}")
        for u in db.query(User).filter(User.id.in_(user_ids)).all()
    } if user_ids else {}

    return [
        {
            "id": r.id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "method": r.method,
            "path": r.path,
            "status_code": r.status_code,
            "duration_ms": r.duration_ms,
            "user_id": r.user_id,
            "user_name": names.get(r.user_id, "—" if r.user_id is None else f"#{r.user_id}"),
            "user_role": r.user_role,
            "client_ip": r.client_ip,
        }
        for r in rows
    ]
