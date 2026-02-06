import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal
from app.core.database import get_db

logger = logging.getLogger(__name__)
from app.core.enums import Role
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.produit_assurance import ProduitAssurance
from app.models.produit_prime_tarif import ProduitPrimeTarif
from app.models.assureur import Assureur
from app.models.historique_prix import HistoriquePrix
from app.models.audit import AuditLog
from app.schemas.produit_assurance import (
    ProduitAssuranceCreate,
    ProduitAssuranceUpdate,
    ProduitAssuranceResponse
)
from app.schemas.produit_prime_tarif import (
    ProduitPrimeTarifBase,
    ProduitPrimeTarifUpdate,
    ProduitPrimeTarifResponse,
)
from app.schemas.historique_prix import HistoriquePrixResponse

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to require admin role"""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required."
        )
    return current_user


def _ensure_assureur(db: Session, assureur_id: Optional[int]) -> Optional[Assureur]:
    if assureur_id is None:
        return None
    assureur = db.query(Assureur).filter(Assureur.id == assureur_id).first()
    if not assureur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assureur sélectionné introuvable"
        )
    return assureur


@router.post("", response_model=ProduitAssuranceResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProduitAssuranceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new product (admin only)"""
    # Check if code already exists
    existing = db.query(ProduitAssurance).filter(ProduitAssurance.code == product_data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with code '{product_data.code}' already exists"
        )
    
    # Validate assureur
    assureur = _ensure_assureur(db, product_data.assureur_id)

    garanties = product_data.garanties or []
    logger.info("create_product: received %d guarantees", len(garanties))

    # Create product
    product_payload = product_data.model_dump()
    product = ProduitAssurance(**product_payload)
    if assureur:
        product.assureur = assureur.nom
    db.add(product)
    db.commit()
    db.refresh(product)
    
    # Create initial price history entry
    historique = HistoriquePrix(
        produit_assurance_id=product.id,
        ancien_prix=None,
        nouveau_prix=product.cout,
        raison_modification="Création du produit",
        modifie_par_user_id=current_user.id
    )
    db.add(historique)
    
    # Create audit log
    role_value = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    audit_log = AuditLog(
        timestamp=datetime.utcnow(),
        method="POST",
        path="/api/v1/admin/products",
        user_id=current_user.id,
        user_role=role_value,
        status_code=201,
        request_body=f"Product created: {product_data.code}"
    )
    db.add(audit_log)
    
    db.commit()
    
    return product


@router.get("", response_model=List[ProduitAssuranceResponse])
async def get_products(
    skip: int = 0,
    limit: int = 100,
    est_actif: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get list of products (admin only)"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Essayer de charger avec la relation assureur_obj
        query = db.query(ProduitAssurance).options(joinedload(ProduitAssurance.assureur_obj))
    except Exception as e:
        # Si erreur avec joinedload (relation ou table n'existe pas), charger sans
        logger.warning(f"Erreur lors du chargement de la relation assureur_obj: {e}")
        query = db.query(ProduitAssurance)
    
    if est_actif is not None:
        query = query.filter(ProduitAssurance.est_actif == est_actif)
    
    try:
        products = query.order_by(ProduitAssurance.created_at.desc()).offset(skip).limit(limit).all()
        logger.info(f"Récupération de {len(products)} produits")
        
        # Sérialiser avec Pydantic, en gérant les erreurs individuellement
        result = []
        for product in products:
            try:
                # Utiliser le schéma Pydantic pour la sérialisation
                product_response = ProduitAssuranceResponse.model_validate(product)
                result.append(product_response)
            except Exception as prod_error:
                logger.warning(f"Erreur lors de la sérialisation du produit {product.id}: {prod_error}", exc_info=True)
                # En cas d'erreur, créer un produit minimal
                try:
                    # Créer un produit minimal sans les relations problématiques
                    product_data = {
                        "id": product.id,
                        "code": product.code,
                        "nom": product.nom,
                        "description": product.description or "",
                        "cout": product.cout,
                        "est_actif": product.est_actif,
                        "assureur_id": product.assureur_id,
                        "assureur": product.assureur if hasattr(product, 'assureur') else None,
                        "created_at": product.created_at,
                        "updated_at": product.updated_at,
                    }
                    product_response = ProduitAssuranceResponse(**product_data)
                    result.append(product_response)
                except Exception as fallback_error:
                    logger.error(f"Impossible de sérialiser le produit {product.id}: {fallback_error}", exc_info=True)
        
        logger.info(f"Retour de {len(result)} produits sérialisés")
        return result
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des produits: {e}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des produits: {str(e)}"
        )


@router.get("/{product_id}", response_model=ProduitAssuranceResponse)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get product by ID (admin only)"""
    try:
        product = (
            db.query(ProduitAssurance)
            .options(joinedload(ProduitAssurance.assureur_obj))
            .filter(ProduitAssurance.id == product_id)
            .first()
        )
    except Exception:
        # Si erreur avec joinedload, charger sans
        product = db.query(ProduitAssurance).filter(ProduitAssurance.id == product_id).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return product


@router.put("/{product_id}", response_model=ProduitAssuranceResponse)
async def update_product(
    product_id: int,
    product_update: ProduitAssuranceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update product (admin only)"""
    product = db.query(ProduitAssurance).filter(ProduitAssurance.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check if code is being changed and if it already exists
    if product_update.code and product_update.code != product.code:
        existing = db.query(ProduitAssurance).filter(
            ProduitAssurance.code == product_update.code,
            ProduitAssurance.id != product_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with code '{product_update.code}' already exists"
            )
    
    # Track price change
    ancien_prix = product.cout
    prix_changed = False

    g = getattr(product_update, "garanties", None)
    logger.info("update_product: received %d guarantees (exclude_unset=True)", len(g) if g is not None else 0)

    # Update fields
    update_data = product_update.model_dump(exclude_unset=True)
    if "garanties" in update_data:
        logger.info("update_product: storing %d guarantees", len(update_data["garanties"]))
    assureur_to_assign = None
    assureur_field_provided = "assureur_id" in update_data
    if assureur_field_provided:
        assureur_to_assign = _ensure_assureur(db, update_data.get("assureur_id"))
    for field, value in update_data.items():
        if field == "cout" and value != ancien_prix:
            prix_changed = True
        setattr(product, field, value)

    if assureur_field_provided:
        product.assureur = assureur_to_assign.nom if assureur_to_assign else None
    
    # Create price history entry if price changed
    if prix_changed:
        historique = HistoriquePrix(
            produit_assurance_id=product.id,
            ancien_prix=ancien_prix,
            nouveau_prix=product.cout,
            raison_modification=product_update.raison_modification or "Modification du prix",
            modifie_par_user_id=current_user.id
        )
        db.add(historique)
    
    # Create audit log
    role_value = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    audit_log = AuditLog(
        timestamp=datetime.utcnow(),
        method="PUT",
        path=f"/api/v1/admin/products/{product_id}",
        user_id=current_user.id,
        user_role=role_value,
        status_code=200,
        request_body=f"Product updated: {product_update.model_dump_json()}"
    )
    db.add(audit_log)
    
    db.commit()
    db.refresh(product)
    
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete product (admin only)"""
    product = db.query(ProduitAssurance).filter(ProduitAssurance.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check if product has active subscriptions
    if product.souscriptions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete product with existing subscriptions"
        )
    
    # Create audit log
    role_value = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    audit_log = AuditLog(
        timestamp=datetime.utcnow(),
        method="DELETE",
        path=f"/api/v1/admin/products/{product_id}",
        user_id=current_user.id,
        user_role=role_value,
        status_code=204,
        request_body=f"Product deleted: {product.code}"
    )
    db.add(audit_log)
    
    db.delete(product)
    db.commit()
    
    return None


@router.get("/{product_id}/price-history", response_model=List[HistoriquePrixResponse])
async def get_price_history(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get price history for a product (admin only)"""
    product = db.query(ProduitAssurance).filter(ProduitAssurance.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    history = db.query(HistoriquePrix).filter(
        HistoriquePrix.produit_assurance_id == product_id
    ).order_by(HistoriquePrix.created_at.desc()).all()
    
    return history


# ========== Tarifs de prime (durée, zone, âge) ==========

@router.get("/{product_id}/tarifs", response_model=List[ProduitPrimeTarifResponse])
async def list_product_tarifs(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Liste des tarifs de prime pour un produit (admin)."""
    product = db.query(ProduitAssurance).filter(ProduitAssurance.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    tarifs = (
        db.query(ProduitPrimeTarif)
        .filter(ProduitPrimeTarif.produit_assurance_id == product_id)
        .order_by(ProduitPrimeTarif.ordre_priorite.desc(), ProduitPrimeTarif.duree_min_jours)
        .all()
    )
    return tarifs


@router.post("/{product_id}/tarifs", response_model=ProduitPrimeTarifResponse, status_code=status.HTTP_201_CREATED)
async def create_product_tarif(
    product_id: int,
    data: ProduitPrimeTarifBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Créer un tarif de prime pour un produit (admin)."""
    product = db.query(ProduitAssurance).filter(ProduitAssurance.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if data.duree_min_jours > data.duree_max_jours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="duree_min_jours ne peut pas être supérieur à duree_max_jours",
        )
    tarif = ProduitPrimeTarif(produit_assurance_id=product_id, **data.model_dump())
    db.add(tarif)
    db.commit()
    db.refresh(tarif)
    return tarif


@router.put("/{product_id}/tarifs/{tarif_id}", response_model=ProduitPrimeTarifResponse)
async def update_product_tarif(
    product_id: int,
    tarif_id: int,
    data: ProduitPrimeTarifUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Modifier un tarif de prime (admin)."""
    tarif = (
        db.query(ProduitPrimeTarif)
        .filter(
            ProduitPrimeTarif.id == tarif_id,
            ProduitPrimeTarif.produit_assurance_id == product_id,
        )
        .first()
    )
    if not tarif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarif not found")
    payload = data.model_dump(exclude_unset=True)
    if payload.get("duree_min_jours") is not None and payload.get("duree_max_jours") is not None:
        dmin, dmax = payload["duree_min_jours"], payload["duree_max_jours"]
        if dmin > dmax:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="duree_min_jours ne peut pas être supérieur à duree_max_jours",
            )
    for k, v in payload.items():
        setattr(tarif, k, v)
    db.commit()
    db.refresh(tarif)
    return tarif


@router.delete("/{product_id}/tarifs/{tarif_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_tarif(
    product_id: int,
    tarif_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Supprimer un tarif de prime (admin)."""
    tarif = (
        db.query(ProduitPrimeTarif)
        .filter(
            ProduitPrimeTarif.id == tarif_id,
            ProduitPrimeTarif.produit_assurance_id == product_id,
        )
        .first()
    )
    if not tarif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarif not found")
    db.delete(tarif)
    db.commit()
    return None
