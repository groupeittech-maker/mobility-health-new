from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.produit_assurance import ProduitAssurance
from app.schemas.produit_assurance import ProduitAssuranceResponse, ProduitQuoteResponse
from app.services.prime_tarif_service import resolve_prime_tarif

router = APIRouter()


async def _get_products_impl(
    skip: int = 0,
    limit: int = 100,
    est_actif: Optional[bool] = True,
    db: Session = Depends(get_db)
):
    """Get list of active products (public endpoint) - implementation"""
    query = db.query(ProduitAssurance).options(joinedload(ProduitAssurance.assureur_obj))
    
    # Par défaut, ne retourner que les produits actifs pour le public
    if est_actif is None:
        est_actif = True
    
    query = query.filter(ProduitAssurance.est_actif == est_actif)
    
    products = query.order_by(ProduitAssurance.nom).offset(skip).limit(limit).all()
    return products


@router.get("/", response_model=List[ProduitAssuranceResponse])
async def get_products(
    skip: int = 0,
    limit: int = 100,
    est_actif: Optional[bool] = True,  # Par défaut, seulement les produits actifs
    db: Session = Depends(get_db)
):
    """Get list of active products (public endpoint) - with trailing slash"""
    return await _get_products_impl(skip, limit, est_actif, db)


# Route explicite sans trailing slash pour éviter les 404
# Utiliser @router.get("") directement au lieu de router.add_api_route
@router.get("", response_model=List[ProduitAssuranceResponse], include_in_schema=False)
async def get_products_no_slash(
    skip: int = 0,
    limit: int = 100,
    est_actif: Optional[bool] = True,
    db: Session = Depends(get_db)
):
    """Get list of active products (public endpoint) - without trailing slash"""
    return await _get_products_impl(skip, limit, est_actif, db)


@router.get("/{product_id}", response_model=ProduitAssuranceResponse)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Get product by ID (public endpoint)"""
    product = (
        db.query(ProduitAssurance)
        .options(joinedload(ProduitAssurance.assureur_obj))
        .filter(
            ProduitAssurance.id == product_id,
            ProduitAssurance.est_actif == True  # Seulement les produits actifs
        )
        .first()
    )
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or not active"
        )
    
    return product


@router.get("/{product_id}/quote", response_model=ProduitQuoteResponse)
async def get_product_quote(
    product_id: int,
    age: Optional[int] = None,
    destination_country_id: Optional[int] = None,
    zone_code: Optional[str] = None,
    duree_jours: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Devis pour un produit selon les caractéristiques (durée, zone, âge).
    Si aucun tarif ne correspond aux intervalles « Tarifs selon durée, zone et âge »,
    on applique le prix et la durée de base du produit.
    """
    product = (
        db.query(ProduitAssurance)
        .filter(
            ProduitAssurance.id == product_id,
            ProduitAssurance.est_actif == True,
        )
        .first()
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or not active",
        )
    prix, from_tarif, duree_min_jours, duree_max_jours = resolve_prime_tarif(
        db,
        product_id=product_id,
        age=age,
        destination_country_id=destination_country_id,
        zone_code=zone_code,
        duree_jours=duree_jours,
    )
    return ProduitQuoteResponse(
        prix=prix,
        duree_validite_jours=product.duree_validite_jours,
        currency=product.currency or "XAF",
        from_tarif=from_tarif,
        duree_min_jours=duree_min_jours,
        duree_max_jours=duree_max_jours,
    )
