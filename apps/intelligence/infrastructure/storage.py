"""MinIO-backed implementation of IReportStorage."""

from __future__ import annotations

import boto3
from botocore.config import Config
from django.conf import settings

from apps.intelligence.domain.repositories import IReportStorage


class MinioReportStorage(IReportStorage):
    """MinIO storage with separate internal (upload) and public (download URL) clients."""

    def __init__(self) -> None:
        scheme = "https" if settings.MINIO_SECURE else "http"
        internal_endpoint = f"{scheme}://{settings.MINIO_ENDPOINT}"
        # browser-accessible endpoint for presigned download URLs
        public_endpoint = getattr(settings, "MINIO_PUBLIC_ENDPOINT", None)
        if not public_endpoint:
            public_endpoint = internal_endpoint.replace("minio:", "localhost:")

        self._bucket: str = settings.MINIO_BUCKET
        creds = {
            "aws_access_key_id": settings.MINIO_ACCESS_KEY,
            "aws_secret_access_key": settings.MINIO_SECRET_KEY,
            "config": Config(signature_version="s3v4"),
            "region_name": "us-east-1",
        }
        self._client = boto3.client("s3", endpoint_url=internal_endpoint, **creds)
        self._public_client = boto3.client("s3", endpoint_url=public_endpoint, **creds)

    def upload(self, file_key: str, content: bytes, content_type: str) -> None:
        """Upload content to MinIO under file_key."""
        self._client.put_object(
            Bucket=self._bucket,
            Key=file_key,
            Body=content,
            ContentType=content_type,
        )

    def generate_presigned_url(self, file_key: str, expires_in: int = 3600) -> str:
        """Return a presigned GET URL using the browser-accessible endpoint."""
        return self._public_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": file_key},
            ExpiresIn=expires_in,
        )
