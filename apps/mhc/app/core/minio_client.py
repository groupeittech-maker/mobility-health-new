import os

from minio import Minio
from minio.error import S3Error
from app.core.config import settings


def _get_minio_endpoint() -> str:
    return getattr(settings, "MINIO_ENDPOINT", None) or os.environ.get("MINIO_ENDPOINT", "localhost:9000")


def _get_minio_access_key() -> str:
    return getattr(settings, "MINIO_ACCESS_KEY", None) or os.environ.get("MINIO_ACCESS_KEY", "minioadmin")


def _get_minio_secret_key() -> str:
    return getattr(settings, "MINIO_SECRET_KEY", None) or os.environ.get("MINIO_SECRET_KEY", "minioadmin")


def _get_minio_secure() -> bool:
    val = getattr(settings, "MINIO_SECURE", None)
    if val is not None:
        return bool(val)
    return os.environ.get("MINIO_SECURE", "false").lower() in ("1", "true", "yes")


minio_client = Minio(
    _get_minio_endpoint(),
    access_key=_get_minio_access_key(),
    secret_key=_get_minio_secret_key(),
    secure=_get_minio_secure(),
)


def get_minio():
    """Dependency for getting Minio client"""
    return minio_client


def ensure_bucket_exists(bucket_name: str):
    """Ensure a bucket exists, create it if it doesn't"""
    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
    except S3Error as e:
        raise e


















