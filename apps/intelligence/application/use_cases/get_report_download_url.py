"""Use case: generate a presigned download URL for a completed report job."""

from __future__ import annotations

import uuid

from apps.intelligence.domain.exceptions import ReportJobNotCompletedError
from apps.intelligence.domain.repositories import IReportJobRepository, IReportStorage


class GetReportDownloadUrlUseCase:
    """Return a presigned URL for the completed report file."""

    def __init__(self, repo: IReportJobRepository, storage: IReportStorage) -> None:
        self._repo = repo
        self._storage = storage

    def execute(self, *, job_id: uuid.UUID) -> str:
        """Fetch the job and return its presigned URL; raises if not completed."""
        job = self._repo.get_by_id(job_id)
        if job.status != "completed":
            raise ReportJobNotCompletedError("Report job has not completed yet.")
        return self._storage.generate_presigned_url(job.file_url)  # type: ignore[arg-type]
