from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.produit_assurance import ProduitAssurance
from app.models.courtier import Courtier
from app.schemas.produit_assurance import (
    ProduitAssuranceResponse,
    ProduitQuoteResponse,
    VoyagePremiumCalculateRequest,
    VoyagePremiumCalculateResponse,
)
from app.services.prime_tarif_service import resolve_prime_tarif_detail
from app.services.produit_selection_assureur import filter_produits_par_territoire_assureur
from app.services.voyage_premium_calculator import (
    VoyagePremiumValidationError,
    calculateInsurancePremium,
    surprime_resolver_from_optional_pcts,
)

router = APIRouter()


async def _get_products_impl(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    est_actif: Optional[bool] = True,
    residence_country_id: Optional[int] = None,
    destination_country_id: Optional[int] = None,
    residence_country_name: Optional[str] = None,
    destination_country_name: Optional[str] = None,
    zone_code: Optional[str] = None,
    filter_by_voyage_assureur: bool = False,
    canal_distribution: str = "assureur",
    courtier_id: Optional[int] = None,
):
    """Get list of active products (public endpoint) - implementation"""
    query = db.query(ProduitAssurance).options(joinedload(ProduitAssurance.assureur_obj))
    
    # Par défaut, ne retourner que les produits actifs pour le public
    if est_actif is None:
        est_actif = True
    
    query = query.filter(ProduitAssurance.est_actif == est_actif)
    
    products = query.order_by(ProduitAssurance.nom).offset(skip).limit(limit).all()

    canal = (canal_distribution or "assureur").strip().lower()
    if canal == "courtier":
        if not courtier_id:
            return []
        courtier = db.query(Courtier).filter(Courtier.id == courtier_id).first()
        if not courtier:
            return []
        products = [p for p in products if p.assureur_id == courtier.assureur_id]
        # Même produit, mais affichage courtier côté UI.
        for p in products:
            p.assureur = courtier.nom

    if filter_by_voyage_assureur:
        products = filter_produits_par_territoire_assureur(
            db,
            products,
            residence_country_id=residence_country_id,
            destination_country_id=destination_country_id,
            residence_country_name=residence_country_name,
            destination_country_name=destination_country_name,
            zone_code=zone_code,
        )
    return products


@router.get("/", response_model=List[ProduitAssuranceResponse])
async def get_products(
    skip: int = 0,
    limit: int = 100,
    est_actif: Optional[bool] = True,  # Par défaut, seulement les produits actifs
    residence_country_id: Optional[int] = None,
    destination_country_id: Optional[int] = None,
    residence_country_name: Optional[str] = None,
    destination_country_name: Optional[str] = None,
    zone_code: Optional[str] = None,
    filter_by_voyage_assureur: bool = False,
    canal_distribution: str = "assureur",
    courtier_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Liste des produits actifs.

    Si ``filter_by_voyage_assureur=true`` et pays résidence/destination fournis,
    ne retourne que les produits dont l'assureur est rattaché au pays attendu :
    pays de résidence (intra-Afrique, RSA/Maghreb, extra-Afrique) ou pays de
    destination (inter-Afrique), selon la zone tarifaire du parcours.
    """
    return await _get_products_impl(
        db,
        skip=skip,
        limit=limit,
        est_actif=est_actif,
        residence_country_id=residence_country_id,
        destination_country_id=destination_country_id,
        residence_country_name=residence_country_name,
        destination_country_name=destination_country_name,
        zone_code=zone_code,
        filter_by_voyage_assureur=filter_by_voyage_assureur,
        canal_distribution=canal_distribution,
        courtier_id=courtier_id,
    )


# Route explicite sans trailing slash pour éviter les 404
# Utiliser @router.get("") directement au lieu de router.add_api_route
@router.get("", response_model=List[ProduitAssuranceResponse], include_in_schema=False)
async def get_products_no_slash(
    skip: int = 0,
    limit: int = 100,
    est_actif: Optional[bool] = True,
    residence_country_id: Optional[int] = None,
    destination_country_id: Optional[int] = None,
    residence_country_name: Optional[str] = None,
    destination_country_name: Optional[str] = None,
    zone_code: Optional[str] = None,
    filter_by_voyage_assureur: bool = False,
    canal_distribution: str = "assureur",
    courtier_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get list of active products (public endpoint) - without trailing slash"""
    return await _get_products_impl(
        db,
        skip=skip,
        limit=limit,
        est_actif=est_actif,
        residence_country_id=residence_country_id,
        destination_country_id=destination_country_id,
        residence_country_name=residence_country_name,
        destination_country_name=destination_country_name,
        zone_code=zone_code,
        filter_by_voyage_assureur=filter_by_voyage_assureur,
        canal_distribution=canal_distribution,
        courtier_id=courtier_id,
    )


@router.post(
    "/premium/calculate",
    response_model=VoyagePremiumCalculateResponse,
    summary="Calcul de prime voyage (grille JSON)",
)
async def post_calculate_voyage_premium(body: VoyagePremiumCalculateRequest):
    """
    Calcule prime grille, frais de services, surprime (sur la prime seulement) et total,
    à partir de la grille canonique, sans produit. Surprimes par tranche d’âge : défauts métier si omis
    (voir /admin/tarification/voyage-reference).
    """
    resolver = surprime_resolver_from_optional_pcts(
        surprime_moins_18_pct=body.surprime_moins_18_pct,
        surprime_70_75_pct=body.surprime_70_75_pct,
        surprime_76_80_pct=body.surprime_76_80_pct,
        surprime_81_89_pct=body.surprime_81_89_pct,
        surprime_hors_standard_pct=body.surprime_hors_standard_pct,
    )
    try:
        r = calculateInsurancePremium(
            body.zone_geographique,
            body.duree_voyage,
            body.age_voyageur,
            surprime_resolver=resolver,
        )
    except VoyagePremiumValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(e), "code": e.code},
        ) from e
    return VoyagePremiumCalculateResponse(
        tarif_base=r.tarif_base,
        frais_services=r.frais_services,
        montant_surprime=r.montant_surprime,
        prime_totale=r.prime_totale,
        tarif_total=r.tarif_total,
        pct_surprime=r.pct_surprime,
        zone_geographique=r.zone_geographique,
        tranche_duree_code=r.tranche_duree_code,
        duree_min_tranche=r.duree_min_tranche,
        duree_max_tranche=r.duree_max_tranche,
    )


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
    destination_country_name: Optional[str] = None,
    residence_country_id: Optional[int] = None,
    residence_country_name: Optional[str] = None,
    zone_code: Optional[str] = None,
    duree_jours: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Devis selon critères voyage (zone, durée, âge) :
    - Si matrice produit (`produit_prime_tarif`) : tarif ligne × (1 + % surprime produit) sauf ligne à âge explicite.
    - Sinon, si la destination / `zone_code` correspond à une zone canonique (INTRA_AFRIQUE, RSA_MAGHREB, etc.)
      et durée 1–90 j : grille JSON voyage (résidence → destination) + surprimes produit sur la prime.
    - Sinon grille finale (`tarification_grille_finale`), grille référence SQL, ou tarif de base × coefficient âge.
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
    detail = resolve_prime_tarif_detail(
        db,
        product_id=product_id,
        age=age,
        destination_country_id=destination_country_id,
        destination_country_name=destination_country_name,
        zone_code=zone_code,
        duree_jours=duree_jours,
        projet=None,
        residence_country_id=residence_country_id,
        user_pays_residence=residence_country_name,
    )
    return ProduitQuoteResponse(
        prix=detail.prix,
        duree_validite_jours=product.duree_validite_jours,
        currency=product.currency or "XAF",
        from_tarif=detail.from_tarif,
        duree_min_jours=detail.duree_min_jours,
        duree_max_jours=detail.duree_max_jours,
        tarif_base=detail.tarif_base,
        coefficient_zone=detail.coefficient_zone,
        coefficient_duree=detail.coefficient_duree,
        coefficient_age=detail.coefficient_age,
        moteur_tarifaire=detail.moteur_tarifaire,
        pct_surprime_applique=detail.pct_surprime_applique,
        tarif_ligne_ht_surprime=detail.tarif_ligne_ht_surprime,
        montant_surprime=detail.montant_surprime,
        tarif_total=detail.prix,
        zone_geographique_code=detail.zone_geographique_code,
        tranche_duree_code=detail.tranche_duree_code,
        frais_services=detail.frais_services,
        prime_assurance=detail.prime_assurance,
    )
