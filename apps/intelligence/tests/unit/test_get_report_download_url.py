"""Tests for GetReportDownloadUrlUseCase."""

from __future__ import annotations

import pytest

from apps.intelligence.application.use_cases.get_report_download_url import GetReportDownloadUrlUseCase
from apps.intelligence.domain.exceptions import ReportJobNotCompletedError

from .conftest import FakeReportJobRepository, FakeReportStorage, make_report_job


class TestGetReportDownloadUrl:
    """Unit tests for GetReportDownloadUrlUseCase."""

    def test_returns_presigned_url_for_completed_job(self) -> None:
        """Returns a presigned URL when the job is completed and has a file_url."""
        job = make_report_job(status="completed", file_url="reports/my-report.csv")
        repo = FakeReportJobRepository()
        repo.create(job)
        storage = FakeReportStorage()
        url = GetReportDownloadUrlUseCase(repo, storage).execute(job_id=job.id)
        assert url.startswith("https://minio.fake/reports/my-report.csv")

    def test_raises_if_job_not_completed(self) -> None:
        """ReportJobNotCompletedError raised when job status is not completed."""
        job = make_report_job(status="processing")
        repo = FakeReportJobRepository()
        repo.create(job)
        storage = FakeReportStorage()
        with pytest.raises(ReportJobNotCompletedError):
            GetReportDownloadUrlUseCase(repo, storage).execute(job_id=job.id)
