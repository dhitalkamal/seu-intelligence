"""MinIO-backed implementation of IReportStorage."""

from __future__ import annotations

import boto3
from botocore.config import Config
from django.conf import settings

from apps.intelligence.domain.repositories import IReportStorage


class MinioReportStorage(IReportStorage):
    """Generates presigned download URLs via a boto3 client pointed at MinIO."""

    def __init__(self) -> None:
        scheme = "https" if settings.MINIO_SECURE else "http"
        self._bucket: str = settings.MINIO_BUCKET
        self._client = boto3.client(
            "s3",
            endpoint_url=f"{scheme}://{settings.MINIO_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

    def upload(self, file_key: str, content: bytes, content_type: str) -> None:
        """Upload content to MinIO under file_key."""
        self._client.put_object(
            Bucket=self._bucket,
            Key=file_key,
            Body=content,
            ContentType=content_type,
        )

    def generate_presigned_url(self, file_key: str, expires_in: int = 3600) -> str:
        """Return a presigned GET URL valid for expires_in seconds."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": file_key},
            ExpiresIn=expires_in,
        )
