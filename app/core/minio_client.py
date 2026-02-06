from minio import Minio
from minio.error import S3Error
from app.core.config import settings

minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE
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


















