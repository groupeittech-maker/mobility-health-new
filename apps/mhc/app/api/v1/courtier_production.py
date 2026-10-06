from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, selectinload
from app.core.database import get_db
from app.core.enums import Role
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.souscription import Souscription
from app.models.courtier_agent import CourtierAgent
from app.models.projet_voyage import ProjetVoyage
from app.schemas.souscription import SouscriptionResponse

router = APIRouter()

# Rôles du portail intermédiaire ayant accès à la production du courtier.
COURTIER_PRODUCTION_ROLES = (Role.AGENT_PRODUCTION_COURTIER, Role.ASSISTANT_SOUSCRIPTION)


def _get_courtier_id_for_agent(db: Session, current_user: User, agent_types) -> Optional[int]:
    """Récupère l'ID du courtier associé à un agent (production, souscription ou sinistre)."""
    try:
        courtier_agent = db.query(CourtierAgent).filter(
            CourtierAgent.user_id == current_user.id,
            CourtierAgent.type_agent.in_(agent_types),
        ).first()
        if courtier_agent:
            return courtier_agent.courtier_id
    except Exception:
        pass
    return None


def require_agent_production_courtier(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Vérifie que l'utilisateur est agent production (ou souscription) d'un courtier."""
    if current_user.role not in COURTIER_PRODUCTION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Courtier production agent access required.",
        )
    courtier_id = _get_courtier_id_for_agent(db, current_user, ('production', 'souscription'))
    if not courtier_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun courtier associé à votre compte. Contactez l'administrateur.",
        )
    return current_user


@router.get("/subscriptions", response_model=List[SouscriptionResponse])
async def get_subscriptions_for_courtier(
    skip: int = 0,
    limit: int = 100,
    statut: Optional[str] = Query(None, description="Filtrer par statut"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_agent_production_courtier),
):
    """
    Obtenir les souscriptions distribuées par le courtier de l'agent.
    Accès en lecture seule pour suivre les demandeurs de souscription.
    """
    courtier_id = _get_courtier_id_for_agent(db, current_user, ('production', 'souscription'))
    if not courtier_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun courtier associé à votre compte. Contactez l'administrateur.",
        )

    query = db.query(Souscription).filter(Souscription.courtier_id == courtier_id)
    if statut:
        query = query.filter(Souscription.statut == statut)

    souscriptions = (
        query
        .options(
            selectinload(Souscription.produit_assurance),
            selectinload(Souscription.projet_voyage),
            selectinload(Souscription.user),
            selectinload(Souscription.questionnaires),
            selectinload(Souscription.paiements),
            selectinload(Souscription.attestations),
        )
        .order_by(Souscription.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return souscriptions


@router.get("/subscriptions/{subscription_id}", response_model=SouscriptionResponse)
async def get_subscription_for_courtier(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_agent_production_courtier),
):
    """
    Obtenir une souscription par ID (uniquement si distribuée par le courtier de l'agent).
    Accès en lecture seule.
    """
    courtier_id = _get_courtier_id_for_agent(db, current_user, ('production', 'souscription'))
    if not courtier_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun courtier associé à votre compte.",
        )

    souscription = (
        db.query(Souscription)
        .options(
            selectinload(Souscription.produit_assurance),
            selectinload(Souscription.projet_voyage),
            selectinload(Souscription.user),
            selectinload(Souscription.questionnaires),
            selectinload(Souscription.paiements),
            selectinload(Souscription.attestations),
        )
        .filter(Souscription.id == subscription_id)
        .first()
    )
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée",
        )
    if souscription.courtier_id != courtier_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette souscription n'est pas distribuée par votre courtier.",
        )
    return souscription


@router.get("/subscriptions/{subscription_id}/workflow")
async def get_subscription_workflow_for_courtier(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_agent_production_courtier),
):
    """
    Obtenir le workflow complet d'une souscription du courtier
    (création, questionnaires, paiement, validations, attestations).
    Accès en lecture seule.
    """
    courtier_id = _get_courtier_id_for_agent(db, current_user, ('production', 'souscription'))
    if not courtier_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun courtier associé à votre compte.",
        )

    souscription = (
        db.query(Souscription)
        .options(
            selectinload(Souscription.produit_assurance),
            selectinload(Souscription.projet_voyage).selectinload(ProjetVoyage.documents),
            selectinload(Souscription.user),
            selectinload(Souscription.questionnaires),
            selectinload(Souscription.paiements),
            selectinload(Souscription.attestations),
        )
        .filter(Souscription.id == subscription_id)
        .first()
    )
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée",
        )
    if souscription.courtier_id != courtier_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette souscription n'est pas distribuée par votre courtier.",
        )

    from app.api.v1.voyages import _serialize_document, _is_internal_minio_url, _build_document_proxy_url
    from app.core.config import settings
    documents_projet = []
    if souscription.projet_voyage and souscription.projet_voyage.documents:
        for doc in sorted(
            souscription.projet_voyage.documents,
            key=lambda d: d.uploaded_at or d.created_at,
            reverse=True,
        ):
            item = _serialize_document(doc).model_dump(mode="json")
            if item.get("download_url") and _is_internal_minio_url(item["download_url"]):
                base = (getattr(settings, "API_PUBLIC_BASE_URL", None) or "").strip().rstrip("/")
                if base:
                    item["download_url"] = _build_document_proxy_url(item["id"])
            documents_projet.append(item)

    produit = souscription.produit_assurance
    return {
        "souscription": {
            "id": souscription.id,
            "numero_souscription": souscription.numero_souscription,
            "statut": souscription.statut,
            "date_debut": souscription.date_debut,
            "date_fin": souscription.date_fin,
            "prix_applique": float(souscription.prix_applique) if souscription.prix_applique else None,
            "created_at": souscription.created_at,
            "validation_medicale": souscription.validation_medicale,
            "validation_technique": souscription.validation_technique,
            "validation_finale": souscription.validation_finale,
        },
        "assure": {
            "id": souscription.user.id if souscription.user else None,
            "full_name": souscription.user.full_name if souscription.user else None,
            "email": souscription.user.email if souscription.user else None,
            "telephone": souscription.user.telephone if souscription.user else None,
        },
        "produit": {
            "id": produit.id if produit else None,
            "nom": produit.nom if produit else None,
            "description": produit.description if produit else None,
        },
        "projet_voyage": {
            "id": souscription.projet_voyage.id if souscription.projet_voyage else None,
            "titre": souscription.projet_voyage.titre if souscription.projet_voyage else None,
            "destination": souscription.projet_voyage.destination if souscription.projet_voyage else None,
            "date_depart": souscription.projet_voyage.date_depart if souscription.projet_voyage else None,
            "date_retour": souscription.projet_voyage.date_retour if souscription.projet_voyage else None,
        },
        "documents_projet_voyage": documents_projet,
        "questionnaires": [
            {"id": q.id, "type": q.type, "created_at": q.created_at}
            for q in (souscription.questionnaires or [])
        ],
        "paiements": [
            {
                "id": p.id,
                "montant": float(p.montant) if p.montant else None,
                "type_paiement": p.type_paiement,
                "statut": p.statut,
                "date_paiement": p.date_paiement,
                "created_at": p.created_at,
            }
            for p in (souscription.paiements or [])
        ],
        "attestations": [
            {
                "id": a.id,
                "numero_attestation": a.numero_attestation,
                "type_attestation": a.type_attestation,
                "est_valide": a.est_valide,
                "created_at": a.created_at,
            }
            for a in (souscription.attestations or [])
        ],
    }
