from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.api.v1.auth import get_current_user, require_admin_user
from app.models.user import User
from app.models.destination import DestinationCountry, DestinationCity
from app.services.country_reference import get_reference_countries
from app.schemas.destination import (
    DestinationCountryCreate,
    DestinationCountryUpdate,
    DestinationCountryResponse,
    DestinationCountryWithCitiesResponse,
    DestinationCityCreate,
    DestinationCityUpdate,
    DestinationCityResponse,
)

router = APIRouter()


# ========== Endpoints publics (pour tous les utilisateurs authentifiés) ==========

@router.get("/countries", response_model=List[DestinationCountryWithCitiesResponse])
async def list_destination_countries(
    actif_seulement: bool = Query(True, description="Ne retourner que les pays actifs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Liste tous les pays de destination avec leurs villes"""
    query = db.query(DestinationCountry)
    
    if actif_seulement:
        query = query.filter(DestinationCountry.est_actif == True)
    
    pays = query.order_by(DestinationCountry.ordre_affichage, DestinationCountry.nom).all()
    
    result = []
    for p in pays:
        villes_query = db.query(DestinationCity).filter(DestinationCity.pays_id == p.id)
        if actif_seulement:
            villes_query = villes_query.filter(DestinationCity.est_actif == True)
        villes = villes_query.order_by(DestinationCity.ordre_affichage, DestinationCity.nom).all()
        
        pays_dict = {
            "id": p.id,
            "code": p.code,
            "nom": p.nom,
            "est_actif": p.est_actif,
            "ordre_affichage": p.ordre_affichage,
            "notes": p.notes,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "villes": [
                {
                    "id": v.id,
                    "pays_id": v.pays_id,
                    "nom": v.nom,
                    "est_actif": v.est_actif,
                    "ordre_affichage": v.ordre_affichage,
                    "notes": v.notes,
                    "created_at": v.created_at,
                    "updated_at": v.updated_at,
                }
                for v in villes
            ]
        }
        result.append(pays_dict)
    
    return result


@router.get("/reference-countries")
async def list_reference_countries(
    force_refresh: bool = Query(False, description="Forcer le rafraîchissement du cache"),
    current_user: User = Depends(get_current_user),
):
    """
    Retourne la liste des pays de référence depuis REST Countries (noms FR si dispos),
    sans dépendre de la base locale. Utilisé pour les sélecteurs de pays de résidence.
    """
    return get_reference_countries(force_refresh=force_refresh)


@router.get("/countries/{country_id}/cities", response_model=List[DestinationCityResponse])
async def list_destination_cities(
    country_id: int,
    actif_seulement: bool = Query(True, description="Ne retourner que les villes actives"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Liste les villes d'un pays de destination"""
    pays = db.query(DestinationCountry).filter(DestinationCountry.id == country_id).first()
    if not pays:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pays de destination non trouvé"
        )
    
    query = db.query(DestinationCity).filter(DestinationCity.pays_id == country_id)
    if actif_seulement:
        query = query.filter(DestinationCity.est_actif == True)
    
    villes = query.order_by(DestinationCity.ordre_affichage, DestinationCity.nom).all()
    return villes


# ========== Endpoints admin (CRUD complet) ==========

@router.post("/admin/countries", response_model=DestinationCountryResponse, status_code=status.HTTP_201_CREATED)
async def create_destination_country(
    country_data: DestinationCountryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    """Créer un nouveau pays de destination"""
    # Vérifier que le code n'existe pas déjà
    existing = db.query(DestinationCountry).filter(DestinationCountry.code == country_data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Un pays avec le code '{country_data.code}' existe déjà"
        )
    
    pays = DestinationCountry(**country_data.model_dump())
    db.add(pays)
    db.commit()
    db.refresh(pays)
    return pays


@router.get("/admin/countries", response_model=List[DestinationCountryWithCitiesResponse])
async def list_all_destination_countries(
    actif_seulement: Optional[bool] = Query(None, description="Filtrer par statut actif"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    """Liste tous les pays de destination (admin)"""
    query = db.query(DestinationCountry)
    
    if actif_seulement is not None:
        query = query.filter(DestinationCountry.est_actif == actif_seulement)
    
    pays = query.order_by(DestinationCountry.ordre_affichage, DestinationCountry.nom).all()
    
    result = []
    for p in pays:
        villes = db.query(DestinationCity).filter(DestinationCity.pays_id == p.id).order_by(
            DestinationCity.ordre_affichage, DestinationCity.nom
        ).all()
        
        pays_dict = {
            "id": p.id,
            "code": p.code,
            "nom": p.nom,
            "est_actif": p.est_actif,
            "ordre_affichage": p.ordre_affichage,
            "notes": p.notes,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "villes": [
                {
                    "id": v.id,
                    "pays_id": v.pays_id,
                    "nom": v.nom,
                    "est_actif": v.est_actif,
                    "ordre_affichage": v.ordre_affichage,
                    "notes": v.notes,
                    "created_at": v.created_at,
                    "updated_at": v.updated_at,
                }
                for v in villes
            ]
        }
        result.append(pays_dict)
    
    return result


@router.get("/admin/countries/{country_id}", response_model=DestinationCountryWithCitiesResponse)
async def get_destination_country(
    country_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    """Récupérer un pays de destination par ID"""
    pays = db.query(DestinationCountry).filter(DestinationCountry.id == country_id).first()
    if not pays:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pays de destination non trouvé"
        )
    
    villes = db.query(DestinationCity).filter(DestinationCity.pays_id == country_id).order_by(
        DestinationCity.ordre_affichage, DestinationCity.nom
    ).all()
    
    return {
        "id": pays.id,
        "code": pays.code,
        "nom": pays.nom,
        "est_actif": pays.est_actif,
        "ordre_affichage": pays.ordre_affichage,
        "notes": pays.notes,
        "created_at": pays.created_at,
        "updated_at": pays.updated_at,
        "villes": [
            {
                "id": v.id,
                "pays_id": v.pays_id,
                "nom": v.nom,
                "est_actif": v.est_actif,
                "ordre_affichage": v.ordre_affichage,
                "notes": v.notes,
                "created_at": v.created_at,
                "updated_at": v.updated_at,
            }
            for v in villes
        ]
    }


@router.put("/admin/countries/{country_id}", response_model=DestinationCountryResponse)
async def update_destination_country(
    country_id: int,
    country_data: DestinationCountryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    """Mettre à jour un pays de destination"""
    pays = db.query(DestinationCountry).filter(DestinationCountry.id == country_id).first()
    if not pays:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pays de destination non trouvé"
        )
    
    # Vérifier que le code n'existe pas déjà (si modifié)
    if country_data.code and country_data.code != pays.code:
        existing = db.query(DestinationCountry).filter(DestinationCountry.code == country_data.code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Un pays avec le code '{country_data.code}' existe déjà"
            )
    
    update_data = country_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pays, field, value)
    
    db.commit()
    db.refresh(pays)
    return pays


@router.delete("/admin/countries/{country_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_destination_country(
    country_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    """Supprimer un pays de destination (supprime aussi les villes associées)"""
    pays = db.query(DestinationCountry).filter(DestinationCountry.id == country_id).first()
    if not pays:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pays de destination non trouvé"
        )
    
    db.delete(pays)
    db.commit()
    return None


# ========== Gestion des villes ==========

@router.post("/admin/cities", response_model=DestinationCityResponse, status_code=status.HTTP_201_CREATED)
async def create_destination_city(
    city_data: DestinationCityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    """Créer une nouvelle ville de destination"""
    # Vérifier que le pays existe
    pays = db.query(DestinationCountry).filter(DestinationCountry.id == city_data.pays_id).first()
    if not pays:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pays de destination non trouvé"
        )
    
    ville = DestinationCity(**city_data.model_dump())
    db.add(ville)
    db.commit()
    db.refresh(ville)
    return ville


@router.put("/admin/cities/{city_id}", response_model=DestinationCityResponse)
async def update_destination_city(
    city_id: int,
    city_data: DestinationCityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    """Mettre à jour une ville de destination"""
    ville = db.query(DestinationCity).filter(DestinationCity.id == city_id).first()
    if not ville:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ville de destination non trouvée"
        )
    
    update_data = city_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ville, field, value)
    
    db.commit()
    db.refresh(ville)
    return ville


@router.delete("/admin/cities/{city_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_destination_city(
    city_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    """Supprimer une ville de destination"""
    ville = db.query(DestinationCity).filter(DestinationCity.id == city_id).first()
    if not ville:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ville de destination non trouvée"
        )
    
    db.delete(ville)
    db.commit()
    return None

