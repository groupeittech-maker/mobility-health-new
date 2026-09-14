from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.enums import StatutPaiement, StatutSouscription
from app.models.assureur import Assureur
from app.models.courtier import Courtier
from app.models.ekyc_session import EkycSession
from app.models.finance_repartition import Repartition
from app.models.paiement import Paiement
from app.models.prestation import Prestation
from app.models.produit_assurance import ProduitAssurance
from app.models.projet_voyage import ProjetVoyage
from app.models.sinistre import Sinistre
from app.models.souscription import Souscription
from app.models.user import User


def _to_key(value):
    if value is None:
        return "unknown"
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _to_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return value


def _apply_date_filters(query, model, start_date: Optional[date], end_date: Optional[date]):
    if start_date:
        dt = datetime.combine(start_date, datetime.min.time())
        query = query.filter(model.created_at >= dt)
    if end_date:
        dt = datetime.combine(end_date, datetime.max.time())
        query = query.filter(model.created_at <= dt)
    return query


def _apply_model_filters(
    query,
    base_model,
    db: Session,
    produit_id: Optional[int] = None,
    assureur_id: Optional[int] = None,
    courtier_id: Optional[int] = None,
    pays: Optional[str] = None,
    canal: Optional[str] = None,
):
    if hasattr(base_model, "produit_assurance_id") and produit_id:
        query = query.filter(base_model.produit_assurance_id == produit_id)
    if hasattr(base_model, "canal_distribution") and canal:
        query = query.filter(base_model.canal_distribution == canal)

    if assureur_id and hasattr(base_model, "produit_assurance_id"):
        query = query.join(ProduitAssurance).filter(ProduitAssurance.assureur_id == assureur_id)
    elif assureur_id and base_model == ProduitAssurance:
        query = query.filter(ProduitAssurance.assureur_id == assureur_id)

    if courtier_id and hasattr(base_model, "courtier_id"):
        query = query.filter(base_model.courtier_id == courtier_id)

    if pays:
        if base_model == User:
            query = query.filter(User.pays_residence == pays)
        elif base_model == Assureur:
            query = query.filter(Assureur.pays == pays)
        elif base_model == Courtier:
            query = query.filter(Courtier.pays == pays)
        elif hasattr(base_model, "produit_assurance_id"):
            query = query.join(ProduitAssurance).join(Assureur).filter(Assureur.pays == pays)

    return query


def _money(value) -> Optional[float]:
    return round(float(value), 2) if value is not None else None


def _safe_div(num, denom):
    if not denom:
        return 0.0
    return round(float(num) / float(denom), 4)


class StatisticsService:
    @staticmethod
    def overview(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        produit_id: Optional[int] = None,
        assureur_id: Optional[int] = None,
        courtier_id: Optional[int] = None,
        pays: Optional[str] = None,
        canal: Optional[str] = None,
    ) -> Dict[str, Any]:
        sq = db.query(Souscription)
        sq = _apply_date_filters(sq, Souscription, start_date, end_date)
        sq = _apply_model_filters(sq, Souscription, db, produit_id, assureur_id, courtier_id, pays, canal)

        pq = db.query(Paiement).join(Souscription)
        pq = _apply_date_filters(pq, Paiement, start_date, end_date)
        pq = _apply_model_filters(pq, Souscription, db, produit_id, assureur_id, courtier_id, pays, canal)

        uq = db.query(User)
        uq = _apply_date_filters(uq, User, start_date, end_date)

        total_subscriptions = sq.count()
        subscriptions_by_status = {
            _to_key(s[0]): int(s[1])
            for s in sq.with_entities(Souscription.statut, func.count(Souscription.id)).group_by(Souscription.statut).all()
        }
        paid_count = subscriptions_by_status.get("active", 0) + subscriptions_by_status.get("en_attente_paiement", 0)

        total_payments = pq.filter(Paiement.statut == StatutPaiement.VALIDE.name).count()
        collected = pq.filter(Paiement.statut == StatutPaiement.VALIDE.name).with_entities(
            func.coalesce(func.sum(Paiement.montant), 0)
        ).scalar() or 0

        pending_amount = sq.filter(Souscription.statut == StatutSouscription.EN_ATTENTE_PAIEMENT.value).with_entities(
            func.coalesce(func.sum(Souscription.prix_applique), 0)
        ).scalar() or 0

        total_users = uq.count()
        conversion = _safe_div(paid_count, total_users) if total_users else 0.0

        total_claims = db.query(Sinistre)
        total_claims = _apply_date_filters(total_claims, Sinistre, start_date, end_date)

        return {
            "period": {"start_date": _to_date(start_date), "end_date": _to_date(end_date)},
            "kpis": {
                "total_subscriptions": total_subscriptions,
                "total_payments": int(total_payments),
                "collected_amount": _money(collected),
                "pending_payment_amount": _money(pending_amount),
                "total_users": total_users,
                "total_claims": total_claims.count(),
                "conversion_rate": round(conversion * 100, 2),
            },
            "subscriptions_by_status": subscriptions_by_status,
            "payments_by_status": {
                _to_key(s[0]): int(s[1])
                for s in pq.with_entities(Paiement.statut, func.count(Paiement.id)).group_by(Paiement.statut).all()
            },
        }

    @staticmethod
    def subscriptions(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        group_by: Optional[str] = None,
        produit_id: Optional[int] = None,
        assureur_id: Optional[int] = None,
        courtier_id: Optional[int] = None,
        pays: Optional[str] = None,
        canal: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = db.query(Souscription)
        query = _apply_date_filters(query, Souscription, start_date, end_date)
        query = _apply_model_filters(query, Souscription, db, produit_id, assureur_id, courtier_id, pays, canal)

        total_count = query.count()
        total_prime = query.with_entities(func.coalesce(func.sum(Souscription.prime_assurance), 0)).scalar() or 0
        total_prix = query.with_entities(func.coalesce(func.sum(Souscription.prix_applique), 0)).scalar() or 0
        avg_prix = query.with_entities(func.coalesce(func.avg(Souscription.prix_applique), 0)).scalar() or 0

        status_breakdown = {
            _to_key(s[0]): int(s[1])
            for s in query.with_entities(Souscription.statut, func.count(Souscription.id)).group_by(Souscription.statut).all()
        }

        canal_breakdown = {
            _to_key(s[0]): int(s[1])
            for s in query.with_entities(Souscription.canal_distribution, func.count(Souscription.id)).group_by(Souscription.canal_distribution).all()
        }

        by_product = []
        for row in (
            query.join(ProduitAssurance)
            .with_entities(ProduitAssurance.nom, func.count(Souscription.id), func.coalesce(func.sum(Souscription.prix_applique), 0))
            .group_by(ProduitAssurance.nom)
            .all()
        ):
            by_product.append({"name": row[0], "count": int(row[1]), "amount": _money(row[2])})

        by_assureur = []
        for row in (
            query.join(ProduitAssurance).join(Assureur)
            .with_entities(Assureur.nom, func.count(Souscription.id), func.coalesce(func.sum(Souscription.prix_applique), 0))
            .group_by(Assureur.nom)
            .all()
        ):
            by_assureur.append({"name": row[0], "count": int(row[1]), "amount": _money(row[2])})

        by_courtier = []
        for row in (
            query.outerjoin(Courtier)
            .with_entities(Courtier.nom, func.count(Souscription.id), func.coalesce(func.sum(Souscription.prix_applique), 0))
            .group_by(Courtier.nom)
            .all()
        ):
            by_courtier.append({"name": row[0] or "Sans courtier", "count": int(row[1]), "amount": _money(row[2])})

        refused = status_breakdown.get(StatutSouscription.REFUSEE.value, 0)
        refused_rate = round((refused / total_count) * 100, 2) if total_count else 0.0

        return {
            "summary": {
                "total_count": total_count,
                "total_prix": _money(total_prix),
                "total_prime": _money(total_prime),
                "average_prix": _money(avg_prix),
                "refused_rate": refused_rate,
            },
            "by_status": status_breakdown,
            "by_canal": canal_breakdown,
            "by_product": by_product,
            "by_assureur": by_assureur,
            "by_courtier": by_courtier,
        }

    @staticmethod
    def payments(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        group_by: Optional[str] = None,
        produit_id: Optional[int] = None,
        assureur_id: Optional[int] = None,
        courtier_id: Optional[int] = None,
        pays: Optional[str] = None,
        canal: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = db.query(Paiement).join(Souscription)
        query = _apply_date_filters(query, Paiement, start_date, end_date)
        query = _apply_model_filters(query, Souscription, db, produit_id, assureur_id, courtier_id, pays, canal)

        total_count = query.count()
        total_amount = query.with_entities(func.coalesce(func.sum(Paiement.montant), 0)).scalar() or 0
        avg_amount = query.with_entities(func.coalesce(func.avg(Paiement.montant), 0)).scalar() or 0

        by_status = {}
        for s, c, m in query.with_entities(Paiement.statut, func.count(Paiement.id), func.coalesce(func.sum(Paiement.montant), 0)).group_by(Paiement.statut).all():
            by_status[_to_key(s)] = {"count": int(c), "amount": _money(m)}

        by_type = {}
        for t, c, m in query.with_entities(Paiement.type_paiement, func.count(Paiement.id), func.coalesce(func.sum(Paiement.montant), 0)).group_by(Paiement.type_paiement).all():
            by_type[_to_key(t)] = {"count": int(c), "amount": _money(m)}

        success_count = by_status.get(StatutPaiement.VALIDE.name, {}).get("count", 0)
        failed_count = by_status.get(StatutPaiement.ECHOUE.name, {}).get("count", 0)
        success_rate = round((success_count / total_count) * 100, 2) if total_count else 0.0

        refund_amount = db.query(func.coalesce(func.sum(Paiement.montant_rembourse), 0)).scalar() or 0

        return {
            "summary": {
                "total_count": total_count,
                "total_amount": _money(total_amount),
                "average_amount": _money(avg_amount),
                "success_rate": success_rate,
                "refund_amount": _money(refund_amount),
            },
            "by_status": by_status,
            "by_type": by_type,
        }

    @staticmethod
    def claims(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        group_by: Optional[str] = None,
        produit_id: Optional[int] = None,
        assureur_id: Optional[int] = None,
        courtier_id: Optional[int] = None,
        pays: Optional[str] = None,
        canal: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = db.query(Sinistre).outerjoin(Souscription)
        query = _apply_date_filters(query, Sinistre, start_date, end_date)
        query = _apply_model_filters(query, Souscription, db, produit_id, assureur_id, courtier_id, pays, canal)

        total_count = query.count()
        status_breakdown = {
            _to_key(s[0]): int(s[1])
            for s in query.with_entities(Sinistre.statut, func.count(Sinistre.id)).group_by(Sinistre.statut).all()
        }

        total_prestations = (
            db.query(Prestation).join(Sinistre)
            .filter(Sinistre.id.in_([s.id for s in query.all()]) if False else True)
        )

        prestation_query = db.query(Prestation).join(Sinistre)
        prestation_query = _apply_date_filters(prestation_query, Prestation, start_date, end_date)
        total_prestation_amount = prestation_query.with_entities(
            func.coalesce(func.sum(Prestation.montant_total), 0)
        ).scalar() or 0
        avg_prestation = prestation_query.with_entities(
            func.coalesce(func.avg(Prestation.montant_total), 0)
        ).scalar() or 0

        active_subscriptions = db.query(Souscription).filter(Souscription.statut == StatutSouscription.ACTIVE.value).count()
        claims_rate = round((total_count / active_subscriptions) * 100, 2) if active_subscriptions else 0.0

        return {
            "summary": {
                "total_claims": total_count,
                "active_subscriptions": active_subscriptions,
                "claims_rate": claims_rate,
                "total_prestation_amount": _money(total_prestation_amount),
                "average_prestation_amount": _money(avg_prestation),
            },
            "by_status": status_breakdown,
            "top_prestations": [
                {"label": row[0], "code": row[1], "count": int(row[2]), "amount": _money(row[3])}
                for row in prestation_query.with_entities(
                    Prestation.libelle, Prestation.code_prestation, func.count(Prestation.id), func.coalesce(func.sum(Prestation.montant_total), 0)
                ).group_by(Prestation.libelle, Prestation.code_prestation).order_by(func.count(Prestation.id).desc()).limit(10).all()
            ],
        }

    @staticmethod
    def reviews(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        produit_id: Optional[int] = None,
        assureur_id: Optional[int] = None,
        courtier_id: Optional[int] = None,
        pays: Optional[str] = None,
        canal: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = db.query(Souscription)
        query = _apply_date_filters(query, Souscription, start_date, end_date)
        query = _apply_model_filters(query, Souscription, db, produit_id, assureur_id, courtier_id, pays, canal)

        medical_pending = query.filter(Souscription.validation_medicale == "pending").count()
        production_pending = query.filter(
            (Souscription.validation_finale == "pending") | (Souscription.validation_technique == "pending")
        ).count()

        medical_approved = query.filter(Souscription.validation_medicale == "approved").count()
        medical_rejected = query.filter(Souscription.validation_medicale == "rejected").count()
        production_approved = query.filter(Souscription.validation_finale == "approved").count()

        approval_rate = round((medical_approved / (medical_approved + medical_rejected)) * 100, 2) if (medical_approved + medical_rejected) else 0.0

        return {
            "summary": {
                "medical_pending": medical_pending,
                "production_pending": production_pending,
                "medical_approved": medical_approved,
                "medical_rejected": medical_rejected,
                "production_approved": production_approved,
                "medical_approval_rate": approval_rate,
            },
            "medical_by_status": {
                _to_key(s[0]): int(s[1])
                for s in query.with_entities(Souscription.validation_medicale, func.count(Souscription.id)).group_by(Souscription.validation_medicale).all()
            },
            "production_by_status": {
                _to_key(s[0]): int(s[1])
                for s in query.with_entities(Souscription.validation_finale, func.count(Souscription.id)).group_by(Souscription.validation_finale).all()
            },
        }

    @staticmethod
    def finance(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        produit_id: Optional[int] = None,
        assureur_id: Optional[int] = None,
        courtier_id: Optional[int] = None,
        pays: Optional[str] = None,
        canal: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = db.query(Souscription)
        query = _apply_date_filters(query, Souscription, start_date, end_date)
        query = _apply_model_filters(query, Souscription, db, produit_id, assureur_id, courtier_id, pays, canal)

        total_prime = query.with_entities(func.coalesce(func.sum(Souscription.prime_assurance), 0)).scalar() or 0
        total_prix = query.with_entities(func.coalesce(func.sum(Souscription.prix_applique), 0)).scalar() or 0
        cout_police = query.with_entities(func.coalesce(func.sum(Souscription.cout_police), 0)).scalar() or 0
        frais_services = query.with_entities(func.coalesce(func.sum(Souscription.frais_services), 0)).scalar() or 0
        taxes_total = query.with_entities(func.coalesce(func.sum(Souscription.taxes_total), 0)).scalar() or 0
        chargement = (cout_police or 0) + (frais_services or 0) + (taxes_total or 0)

        collected = (
            db.query(Paiement)
            .join(Souscription)
            .filter(Paiement.statut == StatutPaiement.VALIDE.name)
        )
        collected = _apply_date_filters(collected, Paiement, start_date, end_date)
        collected = _apply_model_filters(collected, Souscription, db, produit_id, assureur_id, courtier_id, pays, canal)
        total_collected = collected.with_entities(func.coalesce(func.sum(Paiement.montant), 0)).scalar() or 0

        by_assureur = []
        for row in (
            query.join(ProduitAssurance).join(Assureur)
            .with_entities(Assureur.nom, func.coalesce(func.sum(Souscription.prime_assurance), 0), func.count(Souscription.id))
            .group_by(Assureur.nom)
            .all()
        ):
            by_assureur.append({"name": row[0], "prime": _money(row[1]), "count": int(row[2])})

        by_courtier = []
        for row in (
            query.outerjoin(Courtier)
            .with_entities(Courtier.nom, func.coalesce(func.sum(Souscription.prime_assurance), 0), func.count(Souscription.id))
            .group_by(Courtier.nom)
            .all()
        ):
            by_courtier.append({"name": row[0] or "Sans courtier", "prime": _money(row[1]), "count": int(row[2])})

        ekyc_count = db.query(EkycSession)
        ekyc_count = _apply_date_filters(ekyc_count, EkycSession, start_date, end_date)
        ekyc_total = ekyc_count.count()

        return {
            "summary": {
                "total_prix": _money(total_prix),
                "total_prime": _money(total_prime),
                "total_collected": _money(total_collected),
                "cout_police": _money(cout_police),
                "frais_services": _money(frais_services),
                "taxes_total": _money(taxes_total),
                "chargement_total": _money(chargement),
                "ekyc_fees_estimate": _money(ekyc_total * 350),
            },
            "by_assureur": by_assureur,
            "by_courtier": by_courtier,
        }

    @staticmethod
    def users(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        group_by: Optional[str] = None,
        pays: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = db.query(User)
        query = _apply_date_filters(query, User, start_date, end_date)
        if pays:
            query = query.filter(User.pays_residence == pays)

        total = query.count()

        by_country = {
            _to_key(c): int(n)
            for c, n in query.with_entities(User.pays_residence, func.count(User.id)).group_by(User.pays_residence).all()
        }

        subscriptions_per_user = db.query(func.count(Souscription.id)).scalar() / db.query(func.count(User.id)).scalar() if db.query(func.count(User.id)).scalar() else 0

        return {
            "summary": {
                "total_users": total,
                "subscriptions_per_user": round(subscriptions_per_user, 2),
            },
            "by_country": by_country,
            "by_role": {
                _to_key(r): int(n)
                for r, n in query.with_entities(User.role, func.count(User.id)).group_by(User.role).all()
            },
        }

    @staticmethod
    def products(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        produit_id: Optional[int] = None,
        assureur_id: Optional[int] = None,
        courtier_id: Optional[int] = None,
        pays: Optional[str] = None,
        canal: Optional[str] = None,
    ) -> Dict[str, Any]:
        sq = db.query(Souscription)
        sq = _apply_date_filters(sq, Souscription, start_date, end_date)
        sq = _apply_model_filters(sq, Souscription, db, produit_id, assureur_id, courtier_id, pays, canal)

        top_products = [
            {"name": row[0], "count": int(row[1]), "amount": _money(row[2])}
            for row in sq.join(ProduitAssurance)
            .with_entities(ProduitAssurance.nom, func.count(Souscription.id), func.coalesce(func.sum(Souscription.prix_applique), 0))
            .group_by(ProduitAssurance.nom)
            .order_by(func.count(Souscription.id).desc())
            .limit(10)
            .all()
        ]

        top_destinations = []
        for row in (
            sq.join(ProjetVoyage)
            .with_entities(ProjetVoyage.destination, func.count(Souscription.id), func.coalesce(func.sum(Souscription.prix_applique), 0))
            .group_by(ProjetVoyage.destination)
            .order_by(func.count(Souscription.id).desc())
            .limit(10)
            .all()
        ):
            top_destinations.append({"name": row[0], "count": int(row[1]), "amount": _money(row[2])})

        sample = (
            sq.join(ProjetVoyage)
            .with_entities(ProjetVoyage.date_depart, ProjetVoyage.date_retour)
            .limit(500)
            .all()
        )
        durations = []
        for depart, retour in sample:
            if depart and retour:
                durations.append((retour - depart).total_seconds() / 86400)
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "summary": {
                "average_trip_duration_days": round(float(avg_duration), 2) if avg_duration else 0.0,
            },
            "top_products": top_products,
            "top_destinations": top_destinations,
        }

    @staticmethod
    def ekyc(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        query = db.query(EkycSession)
        query = _apply_date_filters(query, EkycSession, start_date, end_date)

        total = query.count()
        by_status = {
            _to_key(s): int(n)
            for s, n in query.with_entities(EkycSession.status, func.count(EkycSession.id)).group_by(EkycSession.status).all()
        }

        success = by_status.get("VERIFIED", 0) + by_status.get("SUCCESS", 0) + by_status.get("APPROVED", 0)
        failed = by_status.get("FAILED", 0) + by_status.get("REJECTED", 0)
        success_rate = round((success / total) * 100, 2) if total else 0.0

        return {
            "summary": {
                "total_sessions": total,
                "success_rate": success_rate,
                "blocked_sessions": failed,
            },
            "by_status": by_status,
        }

    @staticmethod
    def full_report(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        produit_id: Optional[int] = None,
        assureur_id: Optional[int] = None,
        courtier_id: Optional[int] = None,
        pays: Optional[str] = None,
        canal: Optional[str] = None,
        group_by: Optional[str] = None,
        period: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "overview": StatisticsService.overview(db, start_date, end_date, produit_id, assureur_id, courtier_id, pays, canal),
            "subscriptions": StatisticsService.subscriptions(db, start_date, end_date, group_by, produit_id, assureur_id, courtier_id, pays, canal),
            "payments": StatisticsService.payments(db, start_date, end_date, group_by, produit_id, assureur_id, courtier_id, pays, canal),
            "claims": StatisticsService.claims(db, start_date, end_date, group_by, produit_id, assureur_id, courtier_id, pays, canal),
            "reviews": StatisticsService.reviews(db, start_date, end_date, produit_id, assureur_id, courtier_id, pays, canal),
            "finance": StatisticsService.finance(db, start_date, end_date, produit_id, assureur_id, courtier_id, pays, canal),
            "users": StatisticsService.users(db, start_date, end_date, group_by, pays),
            "products": StatisticsService.products(db, start_date, end_date, produit_id, assureur_id, courtier_id, pays, canal),
            "ekyc": StatisticsService.ekyc(db, start_date, end_date),
        }
