from io import BytesIO
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.courtier import Courtier
from app.schemas.courtier import CourtierResponse
from app.services.minio_service import MinioService

router = APIRouter()


@router.get("/", response_model=List[CourtierResponse])
async def list_courtiers(
    assureur_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Courtier)
    if assureur_id is not None:
        query = query.filter(Courtier.assureur_id == assureur_id)
    return query.order_by(Courtier.nom.asc()).all()


@router.get("/{courtier_id}/logo")
async def get_courtier_logo(
    courtier_id: int,
    db: Session = Depends(get_db),
):
    """Retourne l'image du logo d'un courtier (MinIO)."""
    courtier = db.query(Courtier).filter(Courtier.id == courtier_id).first()
    if not courtier or not courtier.logo_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logo non trouvé")
    logo_url = courtier.logo_url.strip()
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier logo introuvable",
        )
    ext = logo_url.split(".")[-1].lower() if "." in logo_url else "png"
    media = f"image/{ext}" if ext in ("png", "gif", "webp") else "image/jpeg"
    return StreamingResponse(BytesIO(data), media_type=media)

