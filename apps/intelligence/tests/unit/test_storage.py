"""Tests for MinioReportStorage."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestMinioReportStorage:
    """Unit tests for MinioReportStorage presigned URL generation."""

    def test_generate_presigned_url_calls_boto3(self) -> None:
        """generate_presigned_url delegates to the boto3 client."""
        fake_client = MagicMock()
        fake_client.generate_presigned_url.return_value = "https://minio.fake/key?X-Amz-Signature=abc"

        with patch("apps.intelligence.infrastructure.storage.boto3.client", return_value=fake_client):
            from apps.intelligence.infrastructure.storage import MinioReportStorage

            storage = MinioReportStorage()
            url = storage.generate_presigned_url("reports/my-file.csv", expires_in=600)

        fake_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": storage._bucket, "Key": "reports/my-file.csv"},
            ExpiresIn=600,
        )
        assert url == "https://minio.fake/key?X-Amz-Signature=abc"

    def test_generate_presigned_url_default_expiry(self) -> None:
        """Default expires_in is 3600 seconds."""
        fake_client = MagicMock()
        fake_client.generate_presigned_url.return_value = "https://minio.fake/key"

        with patch("apps.intelligence.infrastructure.storage.boto3.client", return_value=fake_client):
            from apps.intelligence.infrastructure.storage import MinioReportStorage

            storage = MinioReportStorage()
            storage.generate_presigned_url("reports/file.xlsx")

        _, kwargs = fake_client.generate_presigned_url.call_args
        assert kwargs["ExpiresIn"] == 3600
