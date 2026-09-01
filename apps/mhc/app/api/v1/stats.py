"""
Endpoint API pour les statistiques avec serveur MCP
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.api.v1.auth import get_current_user
from app.models.user import User
import httpx
import os
from app.core.config import settings

router = APIRouter()

# URL du serveur MCP (peut être configuré via variable d'environnement)
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:5000")


class StatsQueryRequest(BaseModel):
    """Requête pour les statistiques en langage naturel"""
    query: str
    user_id: Optional[int] = None


class StatsQueryResponse(BaseModel):
    """Réponse des statistiques"""
    query: str
    sql_query: str
    charts: list
    interpretation_text: str
    summary: dict
    data_count: int
    raw_data: Optional[list] = None


@router.post("/query", response_model=StatsQueryResponse)
async def query_statistics(
    request: StatsQueryRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Interroge le serveur MCP avec une requête en langage naturel
    
    Exemples de requêtes :
    - "Montre-moi mes statistiques d'activité"
    - "Combien de calories ai-je brûlées cette semaine?"
    - "Compare mes activités de marche et de course"
    """
    try:
        # Utiliser l'ID de l'utilisateur connecté si user_id n'est pas fourni
        user_id = request.user_id if request.user_id is not None else current_user.id
        
        # Appeler le serveur MCP (timeout augmenté car Ollama peut prendre 2-3 minutes)
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{MCP_SERVER_URL}/query",
                json={
                    "query": request.query,
                    "user_id": user_id
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Erreur du serveur MCP: {response.text}"
                )
            
            data = response.json()
            
            return StatsQueryResponse(
                query=data.get("query", request.query),
                sql_query=data.get("sql_query", ""),
                charts=data.get("charts", []),
                interpretation_text=data.get("interpretation_text", ""),
                summary=data.get("summary", {}),
                data_count=data.get("data_count", 0),
                raw_data=data.get("raw_data", [])
            )
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Le serveur MCP a pris trop de temps à répondre (timeout > 120s). Ollama peut prendre 2-3 minutes. Réessayez ou utilisez le mode fallback (sans IA) pour des réponses plus rapides."
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Impossible de se connecter au serveur MCP à {MCP_SERVER_URL}. Assurez-vous qu'il est démarré."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la requête: {str(e)}"
        )


@router.get("/schema")
async def get_database_schema(
    current_user: User = Depends(get_current_user)
):
    """Récupère le schéma de la base de données depuis le serveur MCP"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{MCP_SERVER_URL}/schema")
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Erreur du serveur MCP: {response.text}"
                )
            
            return response.json()
            
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Impossible de se connecter au serveur MCP à {MCP_SERVER_URL}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du schéma: {str(e)}"
        )


@router.get("/health")
async def check_mcp_health():
    """Vérifie que le serveur MCP est accessible (sans authentification pour les tests)"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{MCP_SERVER_URL}/health")
            
            if response.status_code == 200:
                return {
                    "status": "ok",
                    "mcp_server": MCP_SERVER_URL,
                    "mcp_status": response.json()
                }
            else:
                return {
                    "status": "error",
                    "mcp_server": MCP_SERVER_URL,
                    "error": f"Code {response.status_code}"
                }
    except httpx.ConnectError:
        return {
            "status": "error",
            "mcp_server": MCP_SERVER_URL,
            "error": f"Impossible de se connecter au serveur MCP à {MCP_SERVER_URL}. Assurez-vous qu'il est démarré."
        }
    except Exception as e:
        return {
            "status": "error",
            "mcp_server": MCP_SERVER_URL,
            "error": str(e)
        }

@router.post("/query-public", response_model=StatsQueryResponse)
async def query_statistics_public(
    request: StatsQueryRequest
):
    """
    Endpoint public pour les requêtes en langage naturel (sans authentification)
    À utiliser pour les tests uniquement. En production, utilisez /query avec authentification.
    """
    try:
        # Appeler directement le serveur MCP (qui n'a pas d'authentification)
        # Timeout augmenté car Ollama peut prendre 2-3 minutes pour répondre
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{MCP_SERVER_URL}/query",
                json={
                    "query": request.query,
                    "user_id": request.user_id
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Erreur du serveur MCP: {response.text}"
                )
            
            data = response.json()
            
            return StatsQueryResponse(
                query=data.get("query", request.query),
                sql_query=data.get("sql_query", ""),
                charts=data.get("charts", []),
                interpretation_text=data.get("interpretation_text", ""),
                summary=data.get("summary", {}),
                data_count=data.get("data_count", 0),
                raw_data=data.get("raw_data", [])
            )
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Le serveur MCP a pris trop de temps à répondre (timeout > 120s). Ollama peut prendre 2-3 minutes. Réessayez ou utilisez le mode fallback (sans IA) pour des réponses plus rapides."
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Impossible de se connecter au serveur MCP à {MCP_SERVER_URL}. Assurez-vous qu'il est démarré."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la requête: {str(e)}"
        )

