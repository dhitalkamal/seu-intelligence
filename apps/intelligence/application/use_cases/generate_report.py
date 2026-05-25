"""Use case: create a pending report job and dispatch the background task."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from apps.intelligence.domain.entities import ReportJobEntity
from apps.intelligence.domain.repositories import IReportJobRepository


class GenerateReportUseCase:
    """Persist a new report job with status=pending, then enqueue the task."""

    def __init__(
        self,
        repo: IReportJobRepository,
        *,
        dispatch_task: Callable[[uuid.UUID], None],
    ) -> None:
        self._repo = repo
        self._dispatch = dispatch_task

    def execute(
        self,
        *,
        requested_by: uuid.UUID,
        report_type: str,
        filters: dict,
        format: str,
    ) -> ReportJobEntity:
        """Create the job record, then kick off the async task."""
        entity = ReportJobEntity(
            id=uuid.uuid4(),
            requested_by=requested_by,
            report_type=report_type,
            filters=filters,
            format=format,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        job = self._repo.create(entity)
        self._dispatch(job.id)
        return job
