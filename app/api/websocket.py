from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.api.v1.sos import manager
from app.core.security import decode_token
from app.core.database import SessionLocal
from app.models.user import User
from app.core.enums import Role

router = APIRouter()


@router.websocket("/ws/sos")
async def websocket_sos(websocket: WebSocket, token: str = Query(None)):
    """
    WebSocket pour les agents sinistre.
    Permet la communication en temps réel des alertes SOS.
    Authentification via query parameter token.
    """
    # Authentification via token dans les query params
    if not token:
        await websocket.close(code=1008, reason="Token manquant")
        return
    
    # Décoder le token pour obtenir l'utilisateur
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Token invalide")
        return
    
    username = payload.get("sub")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.is_active:
            await websocket.close(code=1008, reason="Utilisateur invalide")
            return
        
        # Vérifier que l'utilisateur est un agent sinistre, médecin ou admin
        if user.role not in [Role.SOS_OPERATOR, Role.DOCTOR, Role.ADMIN]:
            await websocket.close(code=1008, reason="Accès non autorisé")
            return
        
        await manager.connect(websocket, user.id)
        
        # Envoyer un message de bienvenue
        await websocket.send_json({
            "type": "connected",
            "message": "Connexion WebSocket établie",
            "user_id": user.id,
            "role": user.role.value
        })
        
        # Écouter les messages
        try:
            while True:
                data = await websocket.receive_text()
                # Traiter les messages entrants si nécessaire
                try:
                    import json
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except:
                    pass
        except WebSocketDisconnect:
            manager.disconnect(websocket, user.id)
    finally:
        db.close()
