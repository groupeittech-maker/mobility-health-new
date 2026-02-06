from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, false
from app.core.database import get_db
from app.core.enums import Role
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.hospital import Hospital
from app.models.hospital_stay import HospitalStay
from app.models.prestation import Prestation
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus, InvoiceHistory
from app.models.notification import Notification
from app.models.sinistre import Sinistre
from app.models.souscription import Souscription
from app.models.produit_assurance import ProduitAssurance
from app.models.assureur import Assureur
from app.services.invoice_history import record_invoice_history, get_invoice_stage
from pydantic import BaseModel, Field
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class InvoiceCreateRequest(BaseModel):
    hospital_id: int
    prestation_ids: List[int] = Field(..., min_items=1)
    date_facture: datetime
    date_echeance: Optional[datetime] = None
    taux_tva: Decimal = Field(default=Decimal("0.20"), ge=0, le=1)  # 20% par défaut
    notes: Optional[str] = None


class InvoiceItemResponse(BaseModel):
    id: int
    libelle: str
    quantite: int
    prix_unitaire: Decimal
    montant_ht: Decimal
    montant_ttc: Decimal
    
    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    id: int
    hospital_id: int
    numero_facture: str
    montant_ht: Decimal
    montant_tva: Decimal
    montant_ttc: Decimal
    date_facture: datetime
    statut: str
    validation_medicale: Optional[str]
    validation_sinistre: Optional[str]
    validation_compta: Optional[str]
    items: List[InvoiceItemResponse]
    
    class Config:
        from_attributes = True


class InvoiceHospitalSummary(BaseModel):
    id: int
    nom: Optional[str] = None
    ville: Optional[str] = None
    pays: Optional[str] = None

    class Config:
        from_attributes = True


class InvoiceStaySummary(BaseModel):
    id: int
    status: Optional[str] = None
    report_status: Optional[str] = None

    class Config:
        from_attributes = True


class InvoiceSinistreSummary(BaseModel):
    id: int
    numero_sinistre: Optional[str] = None
    alerte_id: Optional[int] = None

    class Config:
        from_attributes = True


class InvoiceListItem(BaseModel):
    id: int
    hospital_id: int
    hospital_stay_id: Optional[int] = None
    numero_facture: str
    montant_ht: Decimal
    montant_tva: Decimal
    montant_ttc: Decimal
    statut: str
    validation_medicale: Optional[str] = None
    validation_sinistre: Optional[str] = None
    validation_compta: Optional[str] = None
    date_facture: datetime
    created_at: datetime
    updated_at: datetime
    hospital: Optional[InvoiceHospitalSummary] = None
    stay: Optional[InvoiceStaySummary] = None
    sinistre: Optional[InvoiceSinistreSummary] = None
    client_name: Optional[str] = None
    sinistre_numero: Optional[str] = None

    class Config:
        from_attributes = True


class InvoiceHistoryResponse(BaseModel):
    id: int
    action: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    previous_stage: Optional[str] = None
    new_stage: Optional[str] = None
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ValidationRequest(BaseModel):
    approve: bool = True
    notes: Optional[str] = None


def _notify_role_users(
    db: Session,
    roles: set[Role],
    titre: str,
    message: str,
    relation_id: int,
    relation_type: str = "invoice",
    type_notification: str = "hospital_stay",
):
    if not roles:
        return
    users = (
        db.query(User)
        .filter(
            User.role.in_(list(roles)),
            User.is_active == True,  # noqa: E712
        )
        .all()
    )
    for user in users:
        notification = Notification(
            user_id=user.id,
            type_notification=type_notification,
            titre=titre,
            message=message,
            lien_relation_type=relation_type,
            lien_relation_id=relation_id,
        )
        db.add(notification)


def require_finance_or_admin(current_user: User):
    """Vérifier que l'utilisateur a les droits finance ou admin"""
    if current_user.role not in [
        Role.FINANCE_MANAGER,
        Role.AGENT_COMPTABLE_MH,
        Role.ADMIN,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )


def require_medical_role(current_user: User):
    """Vérifier que l'utilisateur a les droits médicaux"""
    if current_user.role not in [Role.DOCTOR, Role.MEDICAL_REVIEWER, Role.MEDECIN_REFERENT_MH, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux médecins, référents médicaux ou administrateurs."
        )


def _invoice_query_with_access(db: Session, current_user: User):
    base_query = db.query(Invoice).options(
        joinedload(Invoice.hospital),
        joinedload(Invoice.hospital_stay)
        .joinedload(HospitalStay.sinistre),
        joinedload(Invoice.hospital_stay)
        .joinedload(HospitalStay.patient),
    )
    central_roles = {
        Role.ADMIN,
        Role.SOS_OPERATOR,
        Role.AGENT_SINISTRE_MH,
        Role.AGENT_COMPTABLE_MH,
        Role.AGENT_COMPTABLE_ASSUREUR,
        Role.FINANCE_MANAGER,
        Role.MEDICAL_REVIEWER,
        Role.MEDECIN_REFERENT_MH,
    }
    hospital_roles = {
        Role.HOSPITAL_ADMIN,
        Role.AGENT_COMPTABLE_HOPITAL,
    }

    if current_user.role in central_roles:
        if current_user.role == Role.AGENT_COMPTABLE_ASSUREUR:
            assureur_ids = [
                assureur.id
                for assureur in db.query(Assureur).filter(Assureur.agent_comptable_id == current_user.id).all()
            ]
            if not assureur_ids:
                return base_query.filter(false())
            return (
                base_query.join(Invoice.hospital_stay)
                .join(HospitalStay.sinistre)
                .join(Sinistre.souscription)
                .join(Souscription.produit_assurance)
                .filter(ProduitAssurance.assureur_id.in_(assureur_ids))
            )
        return base_query

    if current_user.role in hospital_roles:
        if not current_user.hospital_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Aucun hôpital associé à votre compte.",
            )
        return base_query.filter(Invoice.hospital_id == current_user.hospital_id)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Accès restreint aux équipes médicales, sinistre ou comptables.",
    )


@router.post("/create", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    request: InvoiceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Créer une facture basée sur les prestations"""
    require_finance_or_admin(current_user)
    
    # Vérifier que l'hôpital existe
    hospital = db.query(Hospital).filter(Hospital.id == request.hospital_id).first()
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital not found"
        )
    
    # Récupérer les prestations
    prestations = db.query(Prestation).filter(
        and_(
            Prestation.id.in_(request.prestation_ids),
            Prestation.hospital_id == request.hospital_id,
            Prestation.statut == "pending"
        )
    ).all()
    
    if len(prestations) != len(request.prestation_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some prestations not found or already invoiced"
        )
    
    try:
        # Calculer les montants
        montant_ht = sum(p.montant_total for p in prestations)
        montant_tva = montant_ht * request.taux_tva
        montant_ttc = montant_ht + montant_tva
        
        # Générer le numéro de facture
        numero_facture = f"INV-{hospital.id}-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        # Créer la facture
        invoice = Invoice(
            hospital_id=request.hospital_id,
            numero_facture=numero_facture,
            montant_ht=montant_ht,
            montant_tva=montant_tva,
            montant_ttc=montant_ttc,
            date_facture=request.date_facture,
            date_echeance=request.date_echeance,
            statut=InvoiceStatus.PENDING_MEDICAL,
            validation_medicale="pending",
            validation_sinistre=None,
            validation_compta=None,
            notes=request.notes
        )
        
        db.add(invoice)
        db.flush()  # Pour obtenir l'ID de la facture
        
        # Créer les lignes de facture
        for prestation in prestations:
            item = InvoiceItem(
                invoice_id=invoice.id,
                prestation_id=prestation.id,
                libelle=prestation.libelle,
                quantite=prestation.quantite,
                prix_unitaire=prestation.montant_unitaire,
                montant_ht=prestation.montant_total,
                taux_tva=request.taux_tva,
                montant_ttc=prestation.montant_total * (1 + request.taux_tva)
            )
            db.add(item)
            
            # Marquer la prestation comme facturée
            prestation.statut = "invoiced"
        
        record_invoice_history(
            db,
            invoice,
            action="invoice_created",
            actor_id=current_user.id,
            notes=request.notes,
        )

        db.commit()
        db.refresh(invoice)
        
        # Charger les items
        items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).all()
        hospital_name = hospital.nom if hospital else "l'hôpital"
        message = (
            f"💼 Facture à valider\n\n"
            f"📋 Informations:\n"
            f"• Facture: #{invoice.numero_facture}\n"
            f"• Hôpital: {hospital_name}\n"
            f"• Montant TTC: {invoice.montant_ttc:.2f} €\n"
            f"• Cette facture nécessite votre validation médicale."
        )
        _notify_role_users(
            db,
            {Role.MEDICAL_REVIEWER, Role.MEDECIN_REFERENT_MH},
            "Accord médical requis",
            message,
            relation_id=invoice.id,
            relation_type="invoice",
            type_notification="invoice_medical_review",
        )
        
        # Notifier les agents SOS operator
        _notify_role_users(
            db,
            {Role.SOS_OPERATOR},
            "Nouvelle facture reçue",
            f"📋 Informations:\n• Facture: #{invoice.numero_facture}\n• Hôpital: {hospital.nom}\n• Montant TTC: {invoice.montant_ttc:.2f} €\n• Statut: En attente de validation médicale",
            relation_id=invoice.id,
            type_notification="invoice_received",
        )
        logger.info(f"Invoice {invoice.id} created for hospital {request.hospital_id}")
        
        return InvoiceResponse(
            id=invoice.id,
            hospital_id=invoice.hospital_id,
            numero_facture=invoice.numero_facture,
            montant_ht=invoice.montant_ht,
            montant_tva=invoice.montant_tva,
            montant_ttc=invoice.montant_ttc,
            date_facture=invoice.date_facture,
            statut=invoice.statut,
            validation_medicale=invoice.validation_medicale,
            validation_sinistre=invoice.validation_sinistre,
            validation_compta=invoice.validation_compta,
            items=[
                InvoiceItemResponse(
                    id=item.id,
                    libelle=item.libelle,
                    quantite=item.quantite,
                    prix_unitaire=item.prix_unitaire,
                    montant_ht=item.montant_ht,
                    montant_ttc=item.montant_ttc
                )
                for item in items
            ]
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating invoice: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating invoice: {str(e)}"
        )


# Fonction helper pour la logique de listing
def _list_invoices_logic(
    db: Session,
    current_user: User,
    statut: Optional[str] = None,
    stage: Optional[str] = None,
    hospital_id: Optional[int] = None,
    limit: int = 100,
    skip: int = 0,
):
    """Logique partagée pour lister les factures"""
    query = _invoice_query_with_access(db, current_user)

    if hospital_id:
        query = query.filter(Invoice.hospital_id == hospital_id)

    if stage:
        stage = stage.lower()
        stage_map = {
            "medical": InvoiceStatus.PENDING_MEDICAL,
            "sinistre": InvoiceStatus.PENDING_SINISTRE,
            "compta": InvoiceStatus.PENDING_COMPTA,
        }
        target_status = stage_map.get(stage)
        if not target_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Étape inconnue. Utilisez medical, sinistre ou compta.",
            )
        query = query.filter(Invoice.statut == target_status)
    elif statut:
        query = query.filter(Invoice.statut == statut)

    invoices = (
        query.order_by(Invoice.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    response_items: List[InvoiceListItem] = []
    for invoice in invoices:
        client_name = None
        sinistre_number = None
        stay = invoice.hospital_stay
        if stay:
            if stay.patient:
                client_name = (
                    stay.patient.full_name
                    or stay.patient.username
                    or stay.patient.email
                )
            if stay.sinistre:
                sinistre_number = stay.sinistre.numero_sinistre
        response_items.append(
            InvoiceListItem(
                id=invoice.id,
                hospital_id=invoice.hospital_id,
                hospital_stay_id=invoice.hospital_stay_id,
                numero_facture=invoice.numero_facture,
                montant_ht=invoice.montant_ht,
                montant_tva=invoice.montant_tva,
                montant_ttc=invoice.montant_ttc,
                statut=invoice.statut,
                validation_medicale=invoice.validation_medicale,
                validation_sinistre=invoice.validation_sinistre,
                validation_compta=invoice.validation_compta,
                date_facture=invoice.date_facture,
                created_at=invoice.created_at,
                updated_at=invoice.updated_at,
                hospital=invoice.hospital,
                stay=stay,
                sinistre=stay.sinistre if stay else None,
                client_name=client_name,
                sinistre_numero=sinistre_number,
            )
        )
    return response_items


# Routes pour accepter les deux formats (avec et sans trailing slash)
@router.get("", response_model=List[InvoiceListItem])
async def list_invoices_no_slash(
    statut: Optional[str] = Query(default=None, description="Filtrer par statut brut de la facture."),
    stage: Optional[str] = Query(
        default=None,
        description="Filtrer par étape du workflow (medical, sinistre, compta)."
    ),
    hospital_id: Optional[int] = Query(default=None, description="Limiter aux factures d'un hôpital."),
    limit: int = Query(default=100, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lister les factures accessibles à l'utilisateur courant (sans trailing slash)."""
    return _list_invoices_logic(db, current_user, statut, stage, hospital_id, limit, skip)


@router.get("/", response_model=List[InvoiceListItem])
async def list_invoices(
    statut: Optional[str] = Query(default=None, description="Filtrer par statut brut de la facture."),
    stage: Optional[str] = Query(
        default=None,
        description="Filtrer par étape du workflow (medical, sinistre, compta)."
    ),
    hospital_id: Optional[int] = Query(default=None, description="Limiter aux factures d'un hôpital."),
    limit: int = Query(default=100, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lister les factures accessibles à l'utilisateur courant (avec trailing slash)."""
    return _list_invoices_logic(db, current_user, statut, stage, hospital_id, limit, skip)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consulter une facture et son contenu (lignes) — médecin référent MH, SOS, médecin MH, etc."""
    query = (
        _invoice_query_with_access(db, current_user)
        .options(joinedload(Invoice.items))
        .filter(Invoice.id == invoice_id)
    )
    invoice = query.first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facture introuvable",
        )
    items = [
        InvoiceItemResponse(
            id=item.id,
            libelle=item.libelle,
            quantite=item.quantite,
            prix_unitaire=item.prix_unitaire,
            montant_ht=item.montant_ht,
            montant_ttc=item.montant_ttc,
        )
        for item in (invoice.items or [])
    ]
    return InvoiceResponse(
        id=invoice.id,
        hospital_id=invoice.hospital_id,
        numero_facture=invoice.numero_facture,
        montant_ht=invoice.montant_ht,
        montant_tva=invoice.montant_tva,
        montant_ttc=invoice.montant_ttc,
        date_facture=invoice.date_facture,
        statut=invoice.statut,
        validation_medicale=invoice.validation_medicale,
        validation_sinistre=invoice.validation_sinistre,
        validation_compta=invoice.validation_compta,
        items=items,
    )


@router.get("/{invoice_id}/history", response_model=List[InvoiceHistoryResponse])
async def get_invoice_history(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = _invoice_query_with_access(db, current_user).filter(Invoice.id == invoice_id)
    invoice = query.first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    history_entries = (
        db.query(InvoiceHistory)
        .filter(InvoiceHistory.invoice_id == invoice_id)
        .order_by(InvoiceHistory.created_at.asc(), InvoiceHistory.id.asc())
        .all()
    )
    response: List[InvoiceHistoryResponse] = []
    for entry in history_entries:
        actor_name = None
        if entry.actor:
            actor_name = entry.actor.full_name or entry.actor.username or entry.actor.email
        response.append(
            InvoiceHistoryResponse(
                id=entry.id,
                action=entry.action,
                previous_status=entry.previous_status,
                new_status=entry.new_status,
                previous_stage=entry.previous_stage,
                new_stage=entry.new_stage,
                actor_id=entry.actor_id,
                actor_name=actor_name,
                notes=entry.notes,
                created_at=entry.created_at,
            )
        )
    return response

@router.post("/{invoice_id}/validate_medical", response_model=InvoiceResponse)
async def validate_medical(
    invoice_id: int,
    request: ValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Valider une facture médicalement"""
    require_medical_role(current_user)
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if invoice.statut != InvoiceStatus.PENDING_MEDICAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is not pending medical validation"
        )
    if invoice.validation_medicale in {"approved", "rejected"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Medical validation already processed"
        )
    
    previous_status = invoice.statut
    previous_stage = get_invoice_stage(invoice)

    invoice.validation_medicale = "approved" if request.approve else "rejected"
    invoice.validation_medicale_par = current_user.id
    invoice.validation_medicale_date = datetime.utcnow()
    invoice.validation_medicale_notes = request.notes

    if request.approve:
        invoice.statut = InvoiceStatus.PENDING_SINISTRE
        invoice.validation_sinistre = "pending"
        _notify_role_users(
            db,
            {Role.AGENT_SINISTRE_MH, Role.SOS_OPERATOR},
            "Validation sinistre requise",
            f"La facture #{invoice.numero_facture} est en attente de validation sinistre.",
            relation_id=invoice.id,
        )
    else:
        invoice.statut = InvoiceStatus.REJECTED
        invoice.validation_sinistre = None
        invoice.validation_compta = None
    
    record_invoice_history(
        db,
        invoice,
        action=f"medical_validation_{'approved' if request.approve else 'rejected'}",
        actor_id=current_user.id,
        notes=request.notes,
        previous_status=previous_status,
        previous_stage=previous_stage,
    )
    
    db.commit()
    db.refresh(invoice)
    
    logger.info(f"Invoice {invoice_id} validated medically by user {current_user.id}")
    
    return InvoiceResponse(
        id=invoice.id,
        hospital_id=invoice.hospital_id,
        numero_facture=invoice.numero_facture,
        montant_ht=invoice.montant_ht,
        montant_tva=invoice.montant_tva,
        montant_ttc=invoice.montant_ttc,
        date_facture=invoice.date_facture,
        statut=invoice.statut,
        validation_medicale=invoice.validation_medicale,
        validation_sinistre=invoice.validation_sinistre,
        validation_compta=invoice.validation_compta,
        items=[]  # Charger si nécessaire
    )


@router.post("/{invoice_id}/validate_sinistre", response_model=InvoiceResponse)
async def validate_sinistre(
    invoice_id: int,
    request: ValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Valider une facture pour sinistre (SOS operator, agent sinistre MH)."""
    if current_user.role not in [Role.SOS_OPERATOR, Role.AGENT_SINISTRE_MH, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé au pôle sinistre (SOS / agent sinistre MH) ou admin.",
        )
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if invoice.statut != InvoiceStatus.PENDING_SINISTRE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is not pending sinistre validation"
        )
    if invoice.validation_sinistre in {"approved", "rejected"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sinistre validation already processed"
        )
    
    previous_status = invoice.statut
    previous_stage = get_invoice_stage(invoice)

    invoice.validation_sinistre = "approved" if request.approve else "rejected"
    invoice.validation_sinistre_par = current_user.id
    invoice.validation_sinistre_date = datetime.utcnow()
    invoice.validation_sinistre_notes = request.notes

    if request.approve:
        invoice.statut = InvoiceStatus.PENDING_COMPTA
        invoice.validation_compta = "pending"
        _notify_role_users(
            db,
            {Role.AGENT_COMPTABLE_MH, Role.FINANCE_MANAGER},
            "Validation comptable requise",
            f"La facture #{invoice.numero_facture} doit être traitée par la comptabilité.",
            relation_id=invoice.id,
        )
    else:
        invoice.statut = InvoiceStatus.REJECTED
        invoice.validation_compta = None
    
    record_invoice_history(
        db,
        invoice,
        action=f"sinistre_validation_{'approved' if request.approve else 'rejected'}",
        actor_id=current_user.id,
        notes=request.notes,
        previous_status=previous_status,
        previous_stage=previous_stage,
    )
    
    db.commit()
    db.refresh(invoice)
    
    logger.info(f"Invoice {invoice_id} validated for sinistre by user {current_user.id}")
    
    return InvoiceResponse(
        id=invoice.id,
        hospital_id=invoice.hospital_id,
        numero_facture=invoice.numero_facture,
        montant_ht=invoice.montant_ht,
        montant_tva=invoice.montant_tva,
        montant_ttc=invoice.montant_ttc,
        date_facture=invoice.date_facture,
        statut=invoice.statut,
        validation_medicale=invoice.validation_medicale,
        validation_sinistre=invoice.validation_sinistre,
        validation_compta=invoice.validation_compta,
        items=[]
    )


@router.post("/{invoice_id}/validate_compta", response_model=InvoiceResponse)
async def validate_compta(
    invoice_id: int,
    request: ValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Valider une facture comptablement"""
    require_finance_or_admin(current_user)
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if invoice.statut != InvoiceStatus.PENDING_COMPTA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is not pending compta validation"
        )
    if invoice.validation_compta in {"approved", "rejected"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Compta validation already processed"
        )
    
    previous_status = invoice.statut
    previous_stage = get_invoice_stage(invoice)

    invoice.validation_compta = "approved" if request.approve else "rejected"
    invoice.validation_compta_par = current_user.id
    invoice.validation_compta_date = datetime.utcnow()
    invoice.validation_compta_notes = request.notes
    invoice.statut = InvoiceStatus.VALIDATED if request.approve else InvoiceStatus.REJECTED
    
    record_invoice_history(
        db,
        invoice,
        action=f"compta_validation_{'approved' if request.approve else 'rejected'}",
        actor_id=current_user.id,
        notes=request.notes,
        previous_status=previous_status,
        previous_stage=previous_stage,
    )

    if request.approve and invoice.hospital_stay_id:
        stay = (
            db.query(HospitalStay)
            .options(
                joinedload(HospitalStay.sinistre).joinedload(Sinistre.alerte),
            )
            .filter(HospitalStay.id == invoice.hospital_stay_id)
            .first()
        )
        if stay and stay.sinistre and stay.sinistre.alerte and stay.sinistre.alerte.statut != "resolue":
            stay.sinistre.alerte.statut = "resolue"

    db.commit()
    db.refresh(invoice)

    logger.info(f"Invoice {invoice_id} validated compta by user {current_user.id}")
    
    return InvoiceResponse(
        id=invoice.id,
        hospital_id=invoice.hospital_id,
        numero_facture=invoice.numero_facture,
        montant_ht=invoice.montant_ht,
        montant_tva=invoice.montant_tva,
        montant_ttc=invoice.montant_ttc,
        date_facture=invoice.date_facture,
        statut=invoice.statut,
        validation_medicale=invoice.validation_medicale,
        validation_sinistre=invoice.validation_sinistre,
        validation_compta=invoice.validation_compta,
        items=[]
    )

