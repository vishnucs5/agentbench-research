from __future__ import annotations

import hashlib
import io
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from minio import Minio
from minio.error import S3Error
from packages.domain.config import get_settings


class StorageService:
    def __init__(self):
        settings = get_settings()
        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_secure,
        )
        self._bucket = settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    @property
    def client(self) -> Minio:
        return self._client

    @property
    def bucket(self) -> str:
        return self._bucket

    def compute_sha256(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def compute_sha256_stream(self, stream: io.IOBase) -> tuple[str, bytes]:
        hasher = hashlib.sha256()
        chunks = []
        while chunk := stream.read(8192):
            hasher.update(chunk)
            chunks.append(chunk)
        data = b"".join(chunks)
        return hasher.hexdigest(), data

    def upload_file(
        self,
        object_key: str,
        data: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        stream = io.BytesIO(data)
        self._client.put_object(
            self._bucket,
            object_key,
            stream,
            length=len(data),
            content_type=content_type,
        )
        return object_key

    def download_file(self, object_key: str) -> bytes:
        response = self._client.get_object(self._bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_file(self, object_key: str) -> None:
        self._client.remove_object(self._bucket, object_key)

    def file_exists(self, object_key: str) -> bool:
        try:
            self._client.stat_object(self._bucket, object_key)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise

    def get_presigned_url(self, object_key: str, expires: int = 3600) -> str:
        return self._client.presigned_get_object(self._bucket, object_key, expires=expires)


_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service


@asynccontextmanager
async def get_storage() -> AsyncGenerator[StorageService, None]:
    yield get_storage_service()
