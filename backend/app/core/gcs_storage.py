from datetime import timedelta

import google.auth
import google.auth.transport.requests
from google.cloud import storage as gcs

from app.config import get_settings
from app.core.storage import StorageBackend


def _get_signing_credentials():
    """Return (credentials, service_account_email) refreshed for signing."""
    credentials, _ = google.auth.default()
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)

    sa_email = getattr(credentials, "service_account_email", None)
    if not sa_email:
        import urllib.request as _ur
        req = _ur.Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email",
            headers={"Metadata-Flavor": "Google"},
        )
        sa_email = _ur.urlopen(req, timeout=2).read().decode().strip()

    return credentials, sa_email


class GCSStorage(StorageBackend):
    def __init__(self):
        self.client = gcs.Client()

    def _get_bucket(self, bucket: str):
        settings = get_settings()
        bucket_map = {
            "photos": settings.GCS_BUCKET_PHOTOS,
            "thumbnails": settings.GCS_BUCKET_THUMBNAILS,
            "faces": settings.GCS_BUCKET_FACES,
        }
        bucket_name = bucket_map.get(bucket, bucket)
        return self.client.bucket(bucket_name)

    async def upload(self, bucket: str, key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        gcs_bucket = self._get_bucket(bucket)
        blob = gcs_bucket.blob(key)
        blob.upload_from_string(data, content_type=content_type)
        return f"gs://{gcs_bucket.name}/{key}"

    async def download(self, bucket: str, key: str) -> bytes:
        gcs_bucket = self._get_bucket(bucket)
        blob = gcs_bucket.blob(key)
        return blob.download_as_bytes()

    async def get_url(self, bucket: str, key: str, expires: int = 3600) -> str:
        gcs_bucket = self._get_bucket(bucket)
        blob = gcs_bucket.blob(key)
        try:
            # Works when credentials have a private key (local SA key file)
            return blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expires),
                method="GET",
            )
        except (AttributeError, ValueError):
            # Cloud Run workload identity: sign via IAM API using access token
            credentials, sa_email = _get_signing_credentials()
            return blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expires),
                method="GET",
                service_account_email=sa_email,
                access_token=credentials.token,
            )

    async def delete(self, bucket: str, key: str) -> None:
        gcs_bucket = self._get_bucket(bucket)
        blob = gcs_bucket.blob(key)
        blob.delete()

    async def exists(self, bucket: str, key: str) -> bool:
        gcs_bucket = self._get_bucket(bucket)
        blob = gcs_bucket.blob(key)
        return blob.exists()
