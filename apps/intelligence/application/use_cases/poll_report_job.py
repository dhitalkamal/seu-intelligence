"""Use case: poll a report job by id."""

from __future__ import annotations

import uuid

from apps.intelligence.domain.entities import ReportJobEntity
from apps.intelligence.domain.repositories import IReportJobRepository


class PollReportJobUseCase:
    """Return the current state of a report job."""

    def __init__(self, repo: IReportJobRepository) -> None:
        self._repo = repo

    def execute(self, *, job_id: uuid.UUID) -> ReportJobEntity:
        """Fetch and return the job; raises ReportJobNotFoundError if absent."""
        return self._repo.get_by_id(job_id)
