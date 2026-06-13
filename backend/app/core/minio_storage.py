import io
from datetime import timedelta

from minio import Minio

from app.config import get_settings
from app.core.storage import StorageBackend


class MinIOStorage(StorageBackend):
    def __init__(self):
        settings = get_settings()
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )

    async def upload(self, bucket: str, key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        self.client.put_object(
            bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return f"{bucket}/{key}"

    async def download(self, bucket: str, key: str) -> bytes:
        response = self.client.get_object(bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def get_url(self, bucket: str, key: str, expires: int = 3600) -> str:
        settings = get_settings()
        url = self.client.presigned_get_object(
            bucket, key, expires=timedelta(seconds=expires)
        )
        if not settings.MINIO_USE_SSL:
            url = url.replace("https://", "http://")
        return url

    async def delete(self, bucket: str, key: str) -> None:
        self.client.remove_object(bucket, key)

    async def exists(self, bucket: str, key: str) -> bool:
        try:
            self.client.stat_object(bucket, key)
            return True
        except Exception:
            return False
