from fastapi import APIRouter
from typing import List
import logging
import traceback

logger = logging.getLogger(__name__)
from app.api.v1 import (
    auth,
    users,
    products,
    admin_products,
    admin_subscriptions,
    subscriptions,
    voyages,
    assureurs,
    sos,
    hospitals,
    finance,
    notifications,
    payments,
    questionnaires,
    attestations,
    invoices,
    documents,
    dashboard,
    admin_sinistres,
    admin_assureurs,
    hospital_sinistres,
    destinations,
    assureur_sinistres,
    assureur_production,
    ia,  # Module IA
)

from app.api.v1.notifications import _get_notifications_handler, NotificationResponse

api_router = APIRouter()


@api_router.get("/")
async def api_root():
    """Root endpoint for API v1 avec vérification de l'heure du serveur"""
    from datetime import datetime
    import time
    
    server_time_utc = datetime.utcnow()
    current_year = server_time_utc.year
    is_time_valid = 2020 <= current_year <= 2030
    
    # Vérifier que les routes sont bien enregistrées
    routes_info = {}
    try:
        # Vérifier que le router subscriptions est bien chargé
        from app.api.v1 import subscriptions
        routes_info["subscriptions_router_loaded"] = True
        routes_info["subscriptions_routes_count"] = len(subscriptions.router.routes)
    except Exception as e:
        routes_info["subscriptions_router_error"] = str(e)
    
    try:
        # Vérifier que le router invoices est bien chargé
        from app.api.v1 import invoices
        routes_info["invoices_router_loaded"] = True
        routes_info["invoices_routes_count"] = len(invoices.router.routes)
    except Exception as e:
        routes_info["invoices_router_error"] = str(e)
    
    return {
        "message": "Mobility Health API v1",
        "version": "1.0.0",
        "server_time_utc": server_time_utc.isoformat(),
        "time_valid": is_time_valid,
        "warning": "Vérifiez la synchronisation NTP si time_valid est False" if not is_time_valid else None,
        "routes_status": routes_info,
        "endpoints": {
            "auth": "/api/v1/auth",
            "products": "/api/v1/products",
            "subscriptions": "/api/v1/subscriptions",
            "voyages": "/api/v1/voyages",
            "attestations": "/api/v1/attestations",
            "sos": "/api/v1/sos",
            "hospitals": "/api/v1/hospitals",
            "payments": "/api/v1/payments",
            "notifications": "/api/v1/notifications",
            "dashboard": "/api/v1/dashboard",
            "documents": "/api/v1/documents",
            "invoices": "/api/v1/invoices",
            "ia": "/api/v1/ia",  # Module IA
        },
        "docs": "/docs",
        "health": "/health"
    }


api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(admin_products.router, prefix="/admin/products", tags=["admin-products"])
api_router.include_router(admin_subscriptions.router, prefix="/admin/subscriptions", tags=["admin-subscriptions"])
api_router.include_router(voyages.router, prefix="/voyages", tags=["voyages"])
api_router.include_router(assureurs.router, prefix="/assureurs", tags=["assureurs"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(questionnaires.router, tags=["questionnaires"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(attestations.router, tags=["attestations"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(sos.router, prefix="/sos", tags=["sos"])
api_router.include_router(hospitals.router, prefix="/hospitals", tags=["hospitals"])
api_router.include_router(finance.router, prefix="/finance", tags=["finance"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
# Ajouter une route alternative sans trailing slash pour compatibilité avec redirect_slashes=False
api_router.add_api_route(
    "/notifications",
    _get_notifications_handler,
    methods=["GET"],
    response_model=List[NotificationResponse],
    tags=["notifications"]
)
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(admin_sinistres.router, prefix="/admin/sinistres", tags=["admin-sinistres"])
api_router.include_router(hospital_sinistres.router, prefix="/hospital-sinistres", tags=["hospital-sinistres"])
api_router.include_router(admin_assureurs.router, prefix="/admin/assureurs", tags=["admin-assureurs"])
api_router.include_router(assureur_sinistres.router, prefix="/assureur/sinistres", tags=["assureur-sinistres"])
api_router.include_router(assureur_production.router, prefix="/assureur/production", tags=["assureur-production"])
api_router.include_router(destinations.router, prefix="/destinations", tags=["destinations"])
api_router.include_router(ia.router, tags=["ia"])  # Module IA - Analyse documents
