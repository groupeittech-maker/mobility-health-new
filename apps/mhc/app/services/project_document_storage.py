"""
Stockage des pièces projet : MinIO (par défaut) ou fichiers sur disque si MinIO échoue.

En production, les clients téléchargent souvent via l’API (/voyages/documents/.../download) ;
le serveur doit pouvoir relire les octets depuis MinIO ou depuis un répertoire local monté.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.minio_service import MinioService

logger = logging.getLogger(__name__)

# Valeur de bucket_name en base quand le fichier est sur disque (pas un bucket S3 réel).
LOCAL_PROJECT_DOCUMENTS_BUCKET = "__local_project_documents__"


def local_storage_root_configured() -> bool:
    return bool((getattr(settings, "LOCAL_FILE_STORAGE_ROOT", None) or "").strip())


def _safe_path_under_root(root: str, relative_parts: list[str]) -> Optional[Path]:
    """Construit un chemin sous root ; refuse la sortie du répertoire (path traversal)."""
    root_path = Path(root).resolve()
    candidate = root_path.joinpath(*relative_parts).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError:
        logger.warning("Chemin document local refusé (hors racine): %s", relative_parts)
        return None
    return candidate


def write_local_project_file(projet_voyage_id: int, extension: str, data: bytes) -> Optional[str]:
    """
    Écrit les octets sous {LOCAL_FILE_STORAGE_ROOT}/project-documents/{projet_id}/<uuid>.<ext>.
    Retourne la clé relative (slash) à stocker dans ProjetVoyageDocument.object_name.
    """
    root = (getattr(settings, "LOCAL_FILE_STORAGE_ROOT", None) or "").strip()
    if not root:
        return None
    ext = (extension or "bin").lstrip(".").lower() or "bin"
    if ext not in ("jpg", "jpeg", "png", "gif", "webp", "pdf", "bin"):
        ext = "bin"
    file_name = f"{uuid.uuid4().hex}.{ext}"
    parts = ["project-documents", str(projet_voyage_id), file_name]
    full = _safe_path_under_root(root, parts)
    if full is None:
        return None
    try:
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)
    except OSError as e:
        logger.warning("Écriture fichier local projet impossible %s: %s", full, e)
        return None
    return "/".join(parts)


def read_project_document_bytes(bucket_name: str, object_name: str) -> Optional[bytes]:
    """
    Lit une pièce projet : MinIO ou disque local selon bucket_name.
    """
    if bucket_name == LOCAL_PROJECT_DOCUMENTS_BUCKET:
        root = (getattr(settings, "LOCAL_FILE_STORAGE_ROOT", None) or "").strip()
        if not root or not object_name:
            return None
        relative_parts = [p for p in object_name.replace("\\", "/").split("/") if p and p != "." and p != ".."]
        if not relative_parts:
            return None
        full = _safe_path_under_root(root, relative_parts)
        if full is None or not full.is_file():
            return None
        try:
            return full.read_bytes()
        except OSError as e:
            logger.warning("Lecture fichier local projet impossible %s: %s", full, e)
            return None
    return MinioService.get_file(bucket_name, object_name)
