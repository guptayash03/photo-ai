from abc import ABC, abstractmethod
from typing import Optional

from app.config import get_settings


class StorageBackend(ABC):
    @abstractmethod
    async def upload(self, bucket: str, key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        """Upload file and return the storage path."""
        ...

    @abstractmethod
    async def download(self, bucket: str, key: str) -> bytes:
        """Download file bytes."""
        ...

    @abstractmethod
    async def get_url(self, bucket: str, key: str, expires: int = 3600) -> str:
        """Get a URL to access the file (presigned for MinIO, signed for GCS)."""
        ...

    @abstractmethod
    async def delete(self, bucket: str, key: str) -> None:
        """Delete a file."""
        ...

    @abstractmethod
    async def exists(self, bucket: str, key: str) -> bool:
        """Check if file exists."""
        ...


def get_storage() -> StorageBackend:
    settings = get_settings()
    if settings.STORAGE_BACKEND == "gcs":
        from app.core.gcs_storage import GCSStorage
        return GCSStorage()
    else:
        from app.core.minio_storage import MinIOStorage
        return MinIOStorage()
