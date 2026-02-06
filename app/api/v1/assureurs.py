from typing import List, Optional
from datetime import datetime
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.assureur import Assureur
from app.models.produit_assurance import ProduitAssurance
from app.models.projet_voyage import ProjetVoyage
from app.schemas.assureur import AssureurSummaryForProduct
from app.schemas.produit_assurance import ProduitAssuranceResponse
from app.services.minio_service import MinioService

router = APIRouter()


@router.get("", response_model=List[AssureurSummaryForProduct])
async def list_assureurs(
    db: Session = Depends(get_db),
):
    """
    Liste des assureurs partenaires (pour affichage logos / partenaires sur l'app mobile).
    Données issues de la création des assureurs (admin).
    """
    assureurs = db.query(Assureur).order_by(Assureur.nom.asc()).all()
    return assureurs


@router.get("/search", response_model=List[ProduitAssuranceResponse])
async def search_produits_admissibles(
    projet_voyage_id: Optional[int] = Query(None, description="ID du projet de voyage"),
    destination: Optional[str] = Query(None, description="Destination du voyage"),
    date_depart: Optional[datetime] = Query(None, description="Date de départ"),
    nombre_participants: Optional[int] = Query(1, description="Nombre de participants"),
    db: Session = Depends(get_db)
):
    """
    Rechercher les produits d'assurance admissibles pour un voyage.
    
    Les produits sont filtrés selon :
    - Produits actifs uniquement
    - Optionnellement selon le projet de voyage si fourni
    """
    query = db.query(ProduitAssurance).filter(ProduitAssurance.est_actif == True)
    
    # Si un projet de voyage est fourni, utiliser ses informations
    if projet_voyage_id:
        projet = db.query(ProjetVoyage).filter(ProjetVoyage.id == projet_voyage_id).first()
        if not projet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projet de voyage non trouvé"
            )
        destination = projet.destination
        date_depart = projet.date_depart
        nombre_participants = projet.nombre_participants
    
    # Filtrer les produits selon les critères
    # Pour l'instant, on retourne tous les produits actifs
    # On peut ajouter une logique plus complexe selon la destination, durée, etc.
    
    produits = query.order_by(ProduitAssurance.nom).all()
    
    # Filtrer selon la destination si fournie (exemple de logique)
    if destination:
        # Ici on pourrait avoir une logique de filtrage selon la destination
        # Par exemple, certains produits ne couvrent que certaines destinations
        pass
    
    return produits


@router.get("/{assureur_id}/logo")
async def get_assureur_logo(
    assureur_id: int,
    db: Session = Depends(get_db),
):
    """
    Retourne l'image du logo d'un assureur (stocké en base/MinIO).
    Utilisé par le frontend pour afficher le logo joint (non URL externe).
    """
    assureur = db.query(Assureur).filter(Assureur.id == assureur_id).first()
    if not assureur or not assureur.logo_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logo non trouvé")
    logo_url = assureur.logo_url.strip()
    if logo_url.startswith("http"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logo externe: utilisez l'URL directement.",
        )
    try:
        data = MinioService.get_file(MinioService.BUCKET_LOGOS, logo_url)
    except Exception:
        data = None
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier logo introuvable")
    ext = logo_url.split(".")[-1].lower() if "." in logo_url else "png"
    media = f"image/{ext}" if ext in ("png", "gif", "webp") else "image/jpeg"
    return StreamingResponse(BytesIO(data), media_type=media)
