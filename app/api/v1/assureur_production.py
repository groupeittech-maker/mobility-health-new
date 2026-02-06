from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, selectinload, joinedload
from app.core.database import get_db
from app.core.enums import Role, StatutSouscription
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.souscription import Souscription
from app.models.produit_assurance import ProduitAssurance
from app.models.assureur import Assureur
from app.models.assureur_agent import AssureurAgent
from app.models.projet_voyage import ProjetVoyage
from app.models.questionnaire import Questionnaire
from app.models.paiement import Paiement
from app.models.attestation import Attestation
from app.schemas.souscription import SouscriptionResponse

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


def require_agent_production_assureur(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Dependency pour vérifier que l'utilisateur est agent production assureur"""
    if current_user.role != Role.PRODUCTION_AGENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Production agent assureur access required."
        )
    # Vérifier que l'agent est bien lié à un assureur via AssureurAgent
    assureur_id = _get_assureur_id_for_agent(db, current_user, 'production')
    if not assureur_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun assureur associé à votre compte. Contactez l'administrateur."
        )
    return current_user


@router.get("/subscriptions", response_model=List[SouscriptionResponse])
async def get_subscriptions_for_assureur(
    skip: int = 0,
    limit: int = 100,
    statut: Optional[str] = Query(None, description="Filtrer par statut"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_agent_production_assureur)
):
    """
    Obtenir les souscriptions pour les produits de l'assureur de l'agent.
    Accès en lecture seule pour voir les demandeurs de souscription et la finalisation de leur demande.
    """
    assureur_id = _get_assureur_id_for_agent(db, current_user, 'production')
    
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
    query = db.query(Souscription).filter(
        Souscription.produit_assurance_id.in_(produits_ids)
    )
    
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
            selectinload(Souscription.attestations)
        )
        .order_by(Souscription.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return souscriptions


@router.get("/subscriptions/{subscription_id}", response_model=SouscriptionResponse)
async def get_subscription_for_assureur(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_agent_production_assureur)
):
    """
    Obtenir une souscription par ID (uniquement si liée à un produit de l'assureur de l'agent).
    Accès en lecture seule pour voir tous les détails du workflow de souscription.
    """
    assureur_id = _get_assureur_id_for_agent(db, current_user, 'production')
    
    if not assureur_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun assureur associé à votre compte."
        )
    
    souscription = (
        db.query(Souscription)
        .options(
            selectinload(Souscription.produit_assurance),
            selectinload(Souscription.projet_voyage),
            selectinload(Souscription.user),
            selectinload(Souscription.questionnaires),
            selectinload(Souscription.paiements),
            selectinload(Souscription.attestations)
        )
        .filter(Souscription.id == subscription_id)
        .first()
    )
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Vérifier que la souscription est liée à un produit de l'assureur
    produit = db.query(ProduitAssurance).filter(
        ProduitAssurance.id == souscription.produit_assurance_id
    ).first()
    
    if not produit or produit.assureur_id != assureur_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette souscription n'est pas liée à un produit de votre assureur."
        )
    
    return souscription


@router.get("/subscriptions/{subscription_id}/workflow")
async def get_subscription_workflow_for_assureur(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_agent_production_assureur)
):
    """
    Obtenir le workflow complet d'une souscription (création, questionnaires, paiement, validations, attestations).
    Accès en lecture seule.
    """
    assureur_id = _get_assureur_id_for_agent(db, current_user, 'production')
    
    if not assureur_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun assureur associé à votre compte."
        )
    
    souscription = (
        db.query(Souscription)
        .options(
            selectinload(Souscription.produit_assurance),
            selectinload(Souscription.projet_voyage).selectinload(ProjetVoyage.documents),
            selectinload(Souscription.user),
            selectinload(Souscription.questionnaires),
            selectinload(Souscription.paiements),
            selectinload(Souscription.attestations)
        )
        .filter(Souscription.id == subscription_id)
        .first()
    )
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Vérifier que la souscription est liée à un produit de l'assureur
    produit = db.query(ProduitAssurance).filter(
        ProduitAssurance.id == souscription.produit_assurance_id
    ).first()
    
    if not produit or produit.assureur_id != assureur_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette souscription n'est pas liée à un produit de votre assureur."
        )
    
    # Pièces justificatives du projet de voyage (consultables par l'agent de production)
    from app.api.v1.voyages import _serialize_document
    documents_projet = []
    if souscription.projet_voyage and souscription.projet_voyage.documents:
        for doc in sorted(
            souscription.projet_voyage.documents,
            key=lambda d: d.uploaded_at or d.created_at,
            reverse=True,
        ):
            documents_projet.append(_serialize_document(doc).model_dump(mode="json"))
    
    # Construire le workflow complet
    workflow = {
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
            "id": produit.id,
            "nom": produit.nom,
            "description": produit.description,
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
            {
                "id": q.id,
                "type": q.type,
                "created_at": q.created_at,
            }
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
    
    return workflow

