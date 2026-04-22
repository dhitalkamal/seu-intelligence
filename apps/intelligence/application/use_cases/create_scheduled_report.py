"""Use case: create a recurring report schedule configuration."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from apps.intelligence.domain.entities import ScheduledReportEntity
from apps.intelligence.domain.repositories import IScheduledReportRepository


def _next_run(cron_expression: str, after: datetime) -> datetime:
    """Compute the next datetime after `after` that matches the cron expression."""
    from croniter import CroniterBadCronError, croniter

    try:
        itr = croniter(cron_expression, after)
        return itr.get_next(datetime).replace(tzinfo=timezone.utc)
    except CroniterBadCronError as exc:
        raise ValueError(f"invalid cron expression: {exc}") from exc


class CreateScheduledReportUseCase:
    """Validate the cron expression, compute next_run_at, and persist the schedule."""

    def __init__(self, repo: IScheduledReportRepository) -> None:
        self._repo = repo

    def execute(
        self,
        *,
        event_id: uuid.UUID,
        requested_by: uuid.UUID,
        report_type: str,
        filters: dict,
        format: str,
        cron_expression: str,
    ) -> ScheduledReportEntity:
        """Create and return the persisted schedule entity."""
        now = datetime.now(timezone.utc)
        next_run_at = _next_run(cron_expression, now)

        entity = ScheduledReportEntity(
            id=uuid.uuid4(),
            event_id=event_id,
            requested_by=requested_by,
            report_type=report_type,
            filters=filters,
            format=format,
            cron_expression=cron_expression,
            is_active=True,
            created_at=now,
            next_run_at=next_run_at,
        )
        return self._repo.create(entity)
