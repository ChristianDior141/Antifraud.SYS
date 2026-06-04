"""Pluggable document storage: local disk or S3/MinIO object storage.

Object storage lets every horizontally-scaled backend instance read/write the
same documents (removes the local-disk scaling SPOF). Files are encrypted with
Fernet *before* they reach storage (see endpoints/documents.py), so the stored
object is ciphertext regardless of backend.
"""
import os
from typing import Optional
from app.core.config import settings


class LocalStorage:
    def __init__(self):
        self.base = settings.LOCAL_UPLOAD_DIR
        os.makedirs(self.base, exist_ok=True)

    def _path(self, key: str) -> str:
        return os.path.join(self.base, key)

    def put(self, key: str, data: bytes) -> str:
        path = self._path(key)
        os.makedirs(os.path.dirname(path) or self.base, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return key

    def get(self, key: str) -> bytes:
        with open(self._path(key), "rb") as f:
            return f.read()

    def exists(self, key: str) -> bool:
        return os.path.exists(self._path(key))

    def presigned_get(self, key: str, expires: int = 120) -> Optional[str]:
        return None  # not applicable for local disk


class S3Storage:
    """S3 / MinIO backend (path-style addressing for MinIO compatibility)."""

    def __init__(self):
        import boto3
        from botocore.client import Config

        self.bucket = settings.S3_BUCKET
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=Config(s3={"addressing_style": "path"}),
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self.client.create_bucket(Bucket=self.bucket)
            except Exception:
                pass  # bucket may already exist / be created concurrently

    def put(self, key: str, data: bytes) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key

    def get(self, key: str) -> bytes:
        obj = self.client.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def presigned_get(self, key: str, expires: int = 120) -> Optional[str]:
        """Pre-signed GET URL. NOTE: objects are Fernet-encrypted, so a direct
        download yields ciphertext; use only with server-side-encryption mode."""
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires
        )


_storage = None


def get_storage():
    """Return the configured storage backend (singleton)."""
    global _storage
    if _storage is None:
        _storage = S3Storage() if settings.STORAGE_BACKEND.lower() == "s3" else LocalStorage()
    return _storage
