"""Use case: find due scheduled reports and dispatch generation tasks."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import replace as dc_replace
from datetime import datetime, timezone

from apps.intelligence.domain.entities import ReportJobEntity
from apps.intelligence.domain.repositories import IReportJobRepository, IScheduledReportRepository


def _advance_cron(cron_expression: str, after: datetime) -> datetime:
    """Return the next occurrence of the cron after `after`."""
    from croniter import croniter

    itr = croniter(cron_expression, after)
    return itr.get_next(datetime).replace(tzinfo=timezone.utc)


class TriggerScheduledReportsUseCase:
    """Scan for due schedules, create report jobs, and dispatch background tasks."""

    def __init__(
        self,
        schedule_repo: IScheduledReportRepository,
        job_repo: IReportJobRepository,
        *,
        dispatch_task: Callable[[uuid.UUID], None],
    ) -> None:
        self._schedule_repo = schedule_repo
        self._job_repo = job_repo
        self._dispatch = dispatch_task

    def execute(self, as_of: datetime | None = None) -> int:
        """Trigger all due schedules. Returns the count of dispatched jobs."""
        now = as_of or datetime.now(timezone.utc)
        due = self._schedule_repo.list_due(as_of=now)
        count = 0

        for schedule in due:
            job = ReportJobEntity(
                id=uuid.uuid4(),
                requested_by=schedule.requested_by,
                report_type=schedule.report_type,
                filters=schedule.filters,
                format=schedule.format,
                status="pending",
                created_at=now,
            )
            self._job_repo.create(job)
            self._dispatch(job.id)

            next_run = _advance_cron(schedule.cron_expression, now)
            updated = dc_replace(schedule, last_run_at=now, next_run_at=next_run)
            self._schedule_repo.update(updated)
            count += 1

        return count
