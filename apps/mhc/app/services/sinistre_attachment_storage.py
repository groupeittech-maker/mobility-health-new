"""Stockage des pièces jointes sinistre (MinIO ou disque local)."""
from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.minio_client import ensure_bucket_exists
from app.services.minio_service import MinioService

logger = logging.getLogger(__name__)

BUCKET_SINISTRE_ATTACHMENTS = "sinistre-attachments"
LOCAL_SINISTRE_ATTACHMENTS_BUCKET = "__local_sinistre_attachments__"

MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}


def sanitize_filename(name: str) -> str:
    base = (name or "document").strip().replace("\\", "/").split("/")[-1]
    base = re.sub(r"[^\w.\- ]+", "_", base)
    return base[:200] or "document"


def _local_root() -> str:
    return (getattr(settings, "LOCAL_FILE_STORAGE_ROOT", None) or "").strip()


def _safe_path_under_root(root: str, relative_parts: list[str]) -> Optional[Path]:
    root_path = Path(root).resolve()
    candidate = root_path.joinpath(*relative_parts).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError:
        return None
    return candidate


def write_local_sinistre_attachment(sinistre_id: int, extension: str, data: bytes) -> Optional[str]:
    root = _local_root()
    if not root:
        return None
    ext = (extension or "bin").lstrip(".").lower() or "bin"
    if ext not in ALLOWED_EXTENSIONS:
        ext = "pdf"
    file_name = f"{uuid.uuid4().hex}.{ext}"
    parts = ["sinistre-attachments", str(sinistre_id), file_name]
    full = _safe_path_under_root(root, parts)
    if full is None:
        return None
    try:
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)
    except OSError as exc:
        logger.warning("Écriture pièce jointe sinistre impossible %s: %s", full, exc)
        return None
    return "/".join(parts)


def read_sinistre_attachment_bytes(bucket_name: str, object_name: str) -> Optional[bytes]:
    if bucket_name == LOCAL_SINISTRE_ATTACHMENTS_BUCKET:
        root = _local_root()
        if not root or not object_name:
            return None
        relative_parts = [p for p in object_name.replace("\\", "/").split("/") if p and p not in {".", ".."}]
        if not relative_parts:
            return None
        full = _safe_path_under_root(root, relative_parts)
        if full is None or not full.is_file():
            return None
        try:
            return full.read_bytes()
        except OSError as exc:
            logger.warning("Lecture pièce jointe sinistre impossible %s: %s", full, exc)
            return None
    return MinioService.get_file(bucket_name, object_name)


def store_sinistre_attachment_file(
    sinistre_id: int,
    file_bytes: bytes,
    original_name: str,
    content_type: str,
) -> tuple[str, str]:
    """Persiste le fichier ; retourne (bucket_name, object_name)."""
    sanitized = sanitize_filename(original_name)
    ext = sanitized.rsplit(".", 1)[-1].lower() if "." in sanitized else "pdf"
    if ext not in ALLOWED_EXTENSIONS:
        ct = (content_type or "").lower()
        if "pdf" in ct:
            ext = "pdf"
        elif "png" in ct:
            ext = "png"
        elif "jpeg" in ct or "jpg" in ct:
            ext = "jpg"
        else:
            ext = "pdf"
    object_name = f"sinistres/{sinistre_id}/{uuid.uuid4().hex}_{sanitized}"
    try:
        ensure_bucket_exists(BUCKET_SINISTRE_ATTACHMENTS)
        minio = MinioService()
        minio.upload_file(BUCKET_SINISTRE_ATTACHMENTS, object_name, file_bytes, content_type=content_type)
        return BUCKET_SINISTRE_ATTACHMENTS, object_name
    except Exception as exc:
        logger.warning("Upload MinIO pièce jointe sinistre %s: %s", sinistre_id, exc)
        rel = write_local_sinistre_attachment(sinistre_id, ext, file_bytes)
        if not rel:
            raise RuntimeError("Stockage de fichiers indisponible") from exc
        return LOCAL_SINISTRE_ATTACHMENTS_BUCKET, rel
