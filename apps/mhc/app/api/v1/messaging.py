"""Webhooks de messagerie — Meta WhatsApp Business Cloud API."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.core.config import settings
from app.integrations.messaging.webhook import extract_events, log_events

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhooks/whatsapp")
async def whatsapp_webhook_verify(
    request: Request,
) -> Response:
    """Vérification du webhook par Meta (GET avec hub.challenge)."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if (
        mode == "subscribe"
        and challenge is not None
        and settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
        and token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
    ):
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Vérification du webhook WhatsApp refusée.",
    )


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook_events(request: Request) -> dict:
    """Réception des accusés de livraison et messages entrants.

    Meta exige une réponse 200 rapide ; le traitement se borne à la
    journalisation (les accusés pourront alimenter l'historique des alertes).
    """
    payload = await request.json()
    events = extract_events(payload)
    log_events(events)
    return {"received": True}
