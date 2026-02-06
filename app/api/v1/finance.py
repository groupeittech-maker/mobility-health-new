from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.core.database import get_db
from app.core.enums import Role
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.finance_account import Account
from app.models.finance_movement import Movement
from app.models.finance_repartition import Repartition
from app.models.finance_refund import Refund
from app.models.paiement import Paiement
from app.models.souscription import Souscription
from app.core.enums import StatutPaiement
from app.services.finance_service import FinanceService
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter()


class RepartitionRequest(BaseModel):
    souscription_id: int
    paiement_id: int
    account_id: int


class RepartitionResponse(BaseModel):
    id: int
    souscription_id: int
    paiement_id: int
    montant_total: Decimal
    cle_repartition: str
    repartition_details: dict
    created_at: datetime
    
    class Config:
        from_attributes = True


class RefundRequest(BaseModel):
    paiement_id: int
    account_id: int
    montant: Decimal = Field(..., gt=0)
    raison: str = Field(..., min_length=10)


class RefundResponse(BaseModel):
    id: int
    paiement_id: int
    montant: Decimal
    statut: str
    reference_remboursement: str
    raison: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class BalanceResponse(BaseModel):
    account_id: int
    account_number: str
    account_name: str
    balance: Decimal
    currency: str


class MovementResponse(BaseModel):
    id: int
    account_id: int
    movement_type: str
    amount: Decimal
    description: Optional[str]
    reference: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


def require_finance_role(current_user: User):
    """Vérifier que l'utilisateur a les droits finance"""
    if current_user.role not in [Role.FINANCE_MANAGER, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Finance manager or admin required."
        )


@router.post("/repartition", response_model=RepartitionResponse, status_code=status.HTTP_201_CREATED)
async def create_repartition(
    request: RepartitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculer et créer une répartition selon la clé de répartition du produit"""
    require_finance_role(current_user)
    
    # Vérifier que la souscription existe
    souscription = db.query(Souscription).filter(Souscription.id == request.souscription_id).first()
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Vérifier que le paiement existe et appartient à la souscription
    paiement = db.query(Paiement).filter(
        and_(
            Paiement.id == request.paiement_id,
            Paiement.souscription_id == request.souscription_id
        )
    ).first()
    if not paiement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found or does not belong to this subscription"
        )
    
    # Vérifier que le compte existe
    account = db.query(Account).filter(Account.id == request.account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Traiter la répartition avec transactions ACID
    try:
        repartition = FinanceService.process_repartition(
            db=db,
            souscription_id=request.souscription_id,
            paiement_id=request.paiement_id,
            account_id=request.account_id
        )
        
        return RepartitionResponse(
            id=repartition.id,
            souscription_id=repartition.souscription_id,
            paiement_id=repartition.paiement_id,
            montant_total=repartition.montant_total,
            cle_repartition=repartition.cle_repartition,
            repartition_details=repartition.repartition_details or {},
            created_at=repartition.created_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing repartition: {str(e)}"
        )


@router.post("/refund", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def create_refund(
    request: RefundRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Créer un remboursement en cas de rejet avec transactions ACID"""
    require_finance_role(current_user)
    
    # Vérifier que le paiement existe
    paiement = db.query(Paiement).filter(Paiement.id == request.paiement_id).first()
    if not paiement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Vérifier que le paiement peut être remboursé
    if paiement.statut != StatutPaiement.VALIDE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment must be valid to refund"
        )
    
    # Vérifier que le montant ne dépasse pas le montant du paiement
    if request.montant > paiement.montant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund amount cannot exceed payment amount"
        )
    
    # Vérifier que le compte existe
    account = db.query(Account).filter(Account.id == request.account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Traiter le remboursement avec transactions ACID
    try:
        refund = FinanceService.process_refund(
            db=db,
            paiement_id=request.paiement_id,
            account_id=request.account_id,
            montant=request.montant,
            raison=request.raison,
            processed_by=current_user.id
        )
        
        return RefundResponse(
            id=refund.id,
            paiement_id=refund.paiement_id,
            montant=refund.montant,
            statut=refund.statut,
            reference_remboursement=refund.reference_remboursement,
            raison=refund.raison,
            created_at=refund.created_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing refund: {str(e)}"
        )


@router.get("/accounts/{account_id}/balance", response_model=BalanceResponse)
async def get_account_balance(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir le solde d'un compte"""
    require_finance_role(current_user)
    
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    balance = FinanceService.get_account_balance(db, account_id)
    
    return BalanceResponse(
        account_id=account.id,
        account_number=account.account_number,
        account_name=account.account_name,
        balance=balance,
        currency=account.currency
    )


@router.get("/movements", response_model=List[MovementResponse])
async def get_movements(
    account_id: Optional[int] = Query(None, description="Filter by account ID"),
    movement_type: Optional[str] = Query(None, description="Filter by movement type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir la liste des mouvements financiers avec filtres"""
    require_finance_role(current_user)
    
    query = db.query(Movement)
    
    # Appliquer les filtres
    if account_id:
        query = query.filter(Movement.account_id == account_id)
    if movement_type:
        query = query.filter(Movement.movement_type == movement_type)
    
    # Trier par date décroissante
    query = query.order_by(desc(Movement.created_at))
    
    # Pagination
    movements = query.offset(skip).limit(limit).all()
    
    return [
        MovementResponse(
            id=m.id,
            account_id=m.account_id,
            movement_type=m.movement_type,
            amount=m.amount,
            description=m.description,
            reference=m.reference,
            created_at=m.created_at
        )
        for m in movements
    ]
