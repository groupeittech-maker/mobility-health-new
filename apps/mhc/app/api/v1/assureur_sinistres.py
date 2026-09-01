from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, selectinload, joinedload
from app.core.database import get_db
from app.core.enums import Role
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.sinistre import Sinistre
from app.models.alerte import Alerte
from app.models.souscription import Souscription
from app.models.produit_assurance import ProduitAssurance
from app.models.assureur import Assureur
from app.models.assureur_agent import AssureurAgent
from app.models.sinistre_process_step import SinistreProcessStep
from app.schemas.sinistre import SinistreResponse, SinistreWorkflowStepResponse
from app.schemas.alerte import AlerteResponse
from app.services.sinistre_workflow_service import ensure_workflow_steps

router = APIRouter()


def _get_assureur_id_for_agent(db: Session, current_user: User, agent_type: str) -> Optional[int]:
    """Récupère l'ID de l'assureur associé à un agent (sinistre ou production)"""
    try:
        assureur_agent = db.query(AssureurAgent).filter(
            AssureurAgent.user_id == current_user.id,
            AssureurAgent.type_agent == agent_type
        ).first()
        if assureur_agent:
            return assureur_agent.assureur_id
    except Exception:
        pass
    return None


def require_agent_sinistre_assureur(current_user: User = Depends(get_current_user)) -> User:
    """Dependency pour vérifier que l'utilisateur est agent sinistre assureur"""
    if current_user.role != Role.AGENT_SINISTRE_ASSUREUR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Agent sinistre assureur access required."
        )
    return current_user


@router.get("/sinistres", response_model=List[SinistreResponse])
async def get_sinistres_for_assureur(
    skip: int = 0,
    limit: int = 100,
    statut: Optional[str] = Query(None, description="Filtrer par statut"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_agent_sinistre_assureur)
):
    """
    Obtenir les sinistres des assurés ayant souscrit aux produits de l'assureur de l'agent.
    Accès en lecture seule.
    """
    assureur_id = _get_assureur_id_for_agent(db, current_user, 'sinistre')
    
    if not assureur_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun assureur associé à votre compte. Contactez l'administrateur."
        )
    
    # Récupérer les IDs des produits de cet assureur
    produits_ids = [
        p.id for p in db.query(ProduitAssurance).filter(
            ProduitAssurance.assureur_id == assureur_id
        ).all()
    ]
    
    if not produits_ids:
        return []
    
    # Récupérer les souscriptions pour ces produits
    souscriptions_ids = [
        s.id for s in db.query(Souscription).filter(
            Souscription.produit_assurance_id.in_(produits_ids)
        ).all()
    ]
    
    if not souscriptions_ids:
        return []
    
    # Récupérer les sinistres pour ces souscriptions
    query = db.query(Sinistre).filter(
        Sinistre.souscription_id.in_(souscriptions_ids)
    )
    
    if statut:
        query = query.filter(Sinistre.statut == statut)
    
    sinistres = (
        query
        .options(
            selectinload(Sinistre.alerte),
            selectinload(Sinistre.souscription).selectinload(Souscription.produit_assurance),
            selectinload(Sinistre.souscription).selectinload(Souscription.user),
            selectinload(Sinistre.workflow_steps)
        )
        .order_by(Sinistre.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return sinistres


@router.get("/sinistres/{sinistre_id}", response_model=SinistreResponse)
async def get_sinistre_for_assureur(
    sinistre_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_agent_sinistre_assureur)
):
    """
    Obtenir un sinistre par ID (uniquement si lié à un produit de l'assureur de l'agent).
    Accès en lecture seule.
    """
    assureur_id = _get_assureur_id_for_agent(db, current_user, 'sinistre')
    
    if not assureur_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun assureur associé à votre compte."
        )
    
    sinistre = (
        db.query(Sinistre)
        .options(
            selectinload(Sinistre.alerte),
            selectinload(Sinistre.souscription).selectinload(Souscription.produit_assurance),
            selectinload(Sinistre.souscription).selectinload(Souscription.user),
            selectinload(Sinistre.workflow_steps)
        )
        .filter(Sinistre.id == sinistre_id)
        .first()
    )
    
    if not sinistre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sinistre non trouvé"
        )
    
    # Vérifier que le sinistre est lié à un produit de l'assureur
    if sinistre.souscription_id:
        souscription = db.query(Souscription).filter(
            Souscription.id == sinistre.souscription_id
        ).first()
        if souscription:
            produit = db.query(ProduitAssurance).filter(
                ProduitAssurance.id == souscription.produit_assurance_id
            ).first()
            if produit and produit.assureur_id != assureur_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Ce sinistre n'est pas lié à un produit de votre assureur."
                )
    
    # S'assurer que les étapes du workflow sont créées
    alerte = db.query(Alerte).filter(Alerte.id == sinistre.alerte_id).first() if sinistre.alerte_id else None
    ensure_workflow_steps(db, sinistre, alerte)
    db.commit()
    db.refresh(sinistre)
    
    return sinistre


@router.get("/sinistres/{sinistre_id}/workflow", response_model=List[SinistreWorkflowStepResponse])
async def get_sinistre_workflow_for_assureur(
    sinistre_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_agent_sinistre_assureur)
):
    """
    Obtenir toutes les étapes du workflow d'un sinistre.
    Accès en lecture seule.
    """
    assureur_id = _get_assureur_id_for_agent(db, current_user, 'sinistre')
    
    if not assureur_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun assureur associé à votre compte."
        )
    
    sinistre = db.query(Sinistre).filter(Sinistre.id == sinistre_id).first()
    
    if not sinistre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sinistre non trouvé"
        )
    
    # Vérifier que le sinistre est lié à un produit de l'assureur
    if sinistre.souscription_id:
        souscription = db.query(Souscription).filter(
            Souscription.id == sinistre.souscription_id
        ).first()
        if souscription:
            produit = db.query(ProduitAssurance).filter(
                ProduitAssurance.id == souscription.produit_assurance_id
            ).first()
            if produit and produit.assureur_id != assureur_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Ce sinistre n'est pas lié à un produit de votre assureur."
                )
    
    # S'assurer que les étapes du workflow sont créées
    alerte = db.query(Alerte).filter(Alerte.id == sinistre.alerte_id).first() if sinistre.alerte_id else None
    steps, _ = ensure_workflow_steps(db, sinistre, alerte)
    db.commit()
    
    # Retourner les étapes triées par ordre
    steps.sort(key=lambda s: s.ordre)
    return steps

