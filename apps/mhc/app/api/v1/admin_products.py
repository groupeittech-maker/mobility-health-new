import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal
from app.core.database import get_db

logger = logging.getLogger(__name__)
from app.api.v1.auth import get_current_user
from app.core.permissions import (
    F_COMPTES_PRODUITS,
    LEVEL_CONSULTATION,
    LEVEL_EDITION,
    has_permission,
)
from app.models.user import User
from app.models.produit_assurance import ProduitAssurance
from app.models.produit_prime_tarif import ProduitPrimeTarif
from app.models.tarification import (
    TarificationFenetreDuree,
    TarificationGrilleFinale,
    TarificationTrancheAge,
    TarificationZone,
)
from app.models.assureur import Assureur
from app.models.reassureur import ProduitSurprime
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
from app.schemas.tarification import (
    TarificationGrilleFinaleListResponse,
    TarificationGrilleFinaleRowResponse,
    TarificationGrilleFinaleUpsert,
)
from app.api.v1.admin_tarification import _grille_finale_row_to_response
from app.schemas.historique_prix import HistoriquePrixResponse

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Gestion des produits : niveau 'edition' sur la fonctionnalité comptes_produits."""
    role = getattr(current_user, "role", None)
    if hasattr(role, "value"):
        role = role.value
    if not has_permission(str(role or "user"), F_COMPTES_PRODUITS, LEVEL_EDITION):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Product management required."
        )
    return current_user


def require_products_consult(current_user: User = Depends(get_current_user)) -> User:
    """Consultation des produits : niveau 'consultation' sur comptes_produits."""
    role = getattr(current_user, "role", None)
    if hasattr(role, "value"):
        role = role.value
    if not has_permission(str(role or "user"), F_COMPTES_PRODUITS, LEVEL_CONSULTATION):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Product consultation required."
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
    current_user: User = Depends(require_products_consult)
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
    current_user: User = Depends(require_products_consult)
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
    )
    db.add(audit_log)
    
    db.delete(product)
    db.commit()
    
    return None


@router.get("/{product_id}/price-history", response_model=List[HistoriquePrixResponse])
async def get_price_history(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_products_consult)
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
    current_user: User = Depends(require_products_consult),
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


# ========== Grille finale (tarif devis) par produit ==========


@router.get("/{product_id}/grille-finale", response_model=TarificationGrilleFinaleListResponse)
async def list_product_grille_finale(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_products_consult),
):
    product = db.query(ProduitAssurance).filter(ProduitAssurance.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    cells = (
        db.query(TarificationGrilleFinale)
        .filter(TarificationGrilleFinale.produit_assurance_id == product_id)
        .options(
            joinedload(TarificationGrilleFinale.zone),
            joinedload(TarificationGrilleFinale.fenetre),
            joinedload(TarificationGrilleFinale.tranche_age),
        )
        .all()
    )
    cells.sort(
        key=lambda c: (
            -(c.zone.ordre_affichage if c.zone else 0),
            (c.zone.nom or "").lower() if c.zone else "",
            -(c.fenetre.ordre_priorite if c.fenetre else 0),
            c.fenetre.duree_min_jours if c.fenetre else 0,
            -(c.tranche_age.ordre_priorite if c.tranche_age else 0),
            c.tranche_age_id,
        )
    )
    return TarificationGrilleFinaleListResponse(
        lignes=[_grille_finale_row_to_response(c) for c in cells],
    )


@router.put(
    "/{product_id}/grille-finale/cell",
    response_model=TarificationGrilleFinaleRowResponse,
)
async def upsert_product_grille_finale_cell(
    product_id: int,
    body: TarificationGrilleFinaleUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    product = db.query(ProduitAssurance).filter(ProduitAssurance.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    z = db.query(TarificationZone).filter(TarificationZone.id == body.zone_id).first()
    if not z:
        raise HTTPException(status_code=400, detail="Zone introuvable")
    f = (
        db.query(TarificationFenetreDuree)
        .filter(TarificationFenetreDuree.id == body.fenetre_duree_id)
        .first()
    )
    if not f:
        raise HTTPException(status_code=400, detail="Fenêtre de durée introuvable")
    t = (
        db.query(TarificationTrancheAge)
        .filter(TarificationTrancheAge.id == body.tranche_age_id)
        .first()
    )
    if not t:
        raise HTTPException(status_code=400, detail="Tranche d'âge introuvable")
    coeff = body.coefficient_age if body.coefficient_age is not None else t.coefficient
    now = datetime.utcnow()
    row = (
        db.query(TarificationGrilleFinale)
        .filter(
            TarificationGrilleFinale.produit_assurance_id == product_id,
            TarificationGrilleFinale.zone_id == body.zone_id,
            TarificationGrilleFinale.fenetre_duree_id == body.fenetre_duree_id,
            TarificationGrilleFinale.tranche_age_id == body.tranche_age_id,
        )
        .first()
    )
    if row:
        row.tarif_final = body.tarif_final
        row.coefficient_age = coeff
        row.updated_at = now
    else:
        row = TarificationGrilleFinale(
            produit_assurance_id=product_id,
            zone_id=body.zone_id,
            fenetre_duree_id=body.fenetre_duree_id,
            tranche_age_id=body.tranche_age_id,
            tarif_final=body.tarif_final,
            coefficient_age=coeff,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    row = (
        db.query(TarificationGrilleFinale)
        .options(
            joinedload(TarificationGrilleFinale.zone),
            joinedload(TarificationGrilleFinale.fenetre),
            joinedload(TarificationGrilleFinale.tranche_age),
        )
        .filter(TarificationGrilleFinale.id == row.id)
        .first()
    )
    return _grille_finale_row_to_response(row)


@router.delete("/{product_id}/grille-finale/cell", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_grille_finale_cell(
    product_id: int,
    zone_id: int = Query(..., ge=1),
    fenetre_duree_id: int = Query(..., ge=1),
    tranche_age_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    product = db.query(ProduitAssurance).filter(ProduitAssurance.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    row = (
        db.query(TarificationGrilleFinale)
        .filter(
            TarificationGrilleFinale.produit_assurance_id == product_id,
            TarificationGrilleFinale.zone_id == zone_id,
            TarificationGrilleFinale.fenetre_duree_id == fenetre_duree_id,
            TarificationGrilleFinale.tranche_age_id == tranche_age_id,
        )
        .first()
    )
    if row:
        db.delete(row)
        db.commit()
    return None


# ========== Surprimes par tranche d'âge (table produit) ==========


class ProduitSurprimePayload(BaseModel):
    age_min: int
    age_max: int
    taux_pct: float = 0
    montant_fixe: Optional[float] = None
    formule: Optional[str] = None


@router.get("/{product_id}/surprimes")
async def list_product_surprimes(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_products_consult),
):
    rows = (
        db.query(ProduitSurprime)
        .filter(ProduitSurprime.produit_id == product_id)
        .order_by(ProduitSurprime.age_min)
        .all()
    )
    return [
        {
            "id": r.id,
            "age_min": r.age_min,
            "age_max": r.age_max,
            "taux_pct": float(r.taux_pct) if r.taux_pct is not None else 0,
            "montant_fixe": float(r.montant_fixe) if r.montant_fixe is not None else None,
            "formule": r.formule,
        }
        for r in rows
    ]


@router.put("/{product_id}/surprimes")
async def replace_product_surprimes(
    product_id: int,
    payload: List[ProduitSurprimePayload],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    product = db.query(ProduitAssurance).filter(ProduitAssurance.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    db.query(ProduitSurprime).filter(ProduitSurprime.produit_id == product_id).delete()
    for item in payload:
        db.add(ProduitSurprime(produit_id=product_id, **item.model_dump()))
    db.commit()
    return await list_product_surprimes(product_id, db, current_user)


# ========== Décompte de la prime (maquette : A + B + C + D) ==========


def _pays_defaults(db: Session, product: ProduitAssurance):
    """Paramètres pays de l'assureur utilisés en repli quand le produit ne fixe rien."""
    from app.models.parametre_pays_assureur import ParametrePaysAssureur
    pays = product.pays
    if not pays and product.assureur_obj is not None:
        pays = getattr(product.assureur_obj, "pays", None)
    if not pays:
        return None
    return (
        db.query(ParametrePaysAssureur)
        .filter(ParametrePaysAssureur.pays_assureur == pays, ParametrePaysAssureur.actif == True)
        .first()
    )


@router.get("/{product_id}/decompte")
async def get_product_decompte(
    product_id: int,
    prime_nette: float = Query(..., description="Montant de la prime nette (A)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_products_consult),
):
    """Décomposition A+B+C+D de la prime + commission courtage + répartition."""
    product = db.query(ProduitAssurance).filter(ProduitAssurance.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    defaults = _pays_defaults(db, product)

    a = Decimal(str(prime_nette))
    cout_police = product.cout_police_forfait
    if cout_police is None and defaults is not None:
        cout_police = defaults.cout_police
    b = Decimal(str(cout_police or 0))
    taxe_pct = product.taxe_pct if product.taxe_pct is not None else Decimal("0")
    c = (a * Decimal(str(taxe_pct)) / Decimal("100")).quantize(Decimal("0.01"))
    taxe_add_pct = product.taxe_additionnelle_pct if product.taxe_additionnelle_pct is not None else Decimal("0")
    d = (a * Decimal(str(taxe_add_pct)) / Decimal("100")).quantize(Decimal("0.01"))
    total = a + b + c + d

    courtage_pct = product.commission_courtage_pct if product.commission_courtage_pct is not None else Decimal("0")
    commission_courtage = (a * Decimal(str(courtage_pct)) / Decimal("100")).quantize(Decimal("0.01"))

    cession_pct = product.cession_reassureur_pct
    if cession_pct is None and defaults is not None:
        cession_pct = defaults.reassureur_pct
    cession_pct = Decimal(str(cession_pct or 0))
    cession = (a * cession_pct / Decimal("100")).quantize(Decimal("0.01"))

    retention_pct = Decimal(str(product.retention_assureur_pct or 0))
    retention = (a * retention_pct / Decimal("100")).quantize(Decimal("0.01"))

    comm_cession_pct = Decimal(str(product.commission_cession_pct or 0))
    commission_cession = (cession * comm_cession_pct / Decimal("100")).quantize(Decimal("0.01"))

    mhc = (a - cession - retention).quantize(Decimal("0.01"))

    return {
        "prime_nette": float(a),
        "decompte": [
            {"code": "A", "label": "Prime nette", "montant": float(a)},
            {"code": "B", "label": "Coût de police", "montant": float(b)},
            {"code": "C", "label": f"Taxe ({taxe_pct}%)", "montant": float(c)},
            {"code": "D", "label": f"Taxe additionnelle ({taxe_add_pct}%)", "montant": float(d)},
        ],
        "prime_totale": float(total),
        "commission_courtage": {
            "taux_pct": float(courtage_pct),
            "montant": float(commission_courtage),
            "formule": f"{a} × {courtage_pct}%",
        },
        "repartition": [
            {"beneficiaire": "Réassureur (cession)", "base": "Prime nette", "taux_pct": float(cession_pct), "montant": float(cession)},
            {"beneficiaire": "Commission de cession", "base": "Cession", "taux_pct": float(comm_cession_pct), "montant": float(commission_cession)},
            {"beneficiaire": "Assureur (rétention)", "base": "Prime nette", "taux_pct": float(retention_pct), "montant": float(retention)},
            {"beneficiaire": "Intermédiaire (courtage)", "base": "Prime nette", "taux_pct": float(courtage_pct), "montant": float(commission_courtage)},
            {"beneficiaire": "Coût de police (MHC)", "base": "Forfait", "taux_pct": None, "montant": float(b)},
            {"beneficiaire": "Fisc (taxes C+D)", "base": "Taxes", "taux_pct": None, "montant": float(c + d)},
            {"beneficiaire": "Reliquat MHC", "base": "Prime nette", "taux_pct": None, "montant": float(mhc)},
        ],
        "sources": {
            "cout_police": "produit" if product.cout_police_forfait is not None else ("pays" if defaults else None),
            "cession": "produit" if product.cession_reassureur_pct is not None else ("pays" if defaults else None),
        },
    }
