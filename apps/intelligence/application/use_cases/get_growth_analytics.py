"""Use case: aggregate analytics events into growth metrics by day."""

from __future__ import annotations

import uuid
from datetime import datetime

from apps.intelligence.domain.repositories import IAnalyticsGrowthRepository


class GetGrowthAnalyticsUseCase:
    """Compute registration and revenue growth for a tracked event."""

    def __init__(self, growth_repo: IAnalyticsGrowthRepository) -> None:
        self._growth_repo = growth_repo

    def execute(
        self,
        *,
        event_id: uuid.UUID,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> dict:
        """Return {"registrations": {"total", "by_day"}, "revenue": {"total", "by_day"}}."""
        reg_rows = self._growth_repo.aggregate_daily(event_id, "registration.", since, until)
        rev_rows = self._growth_repo.aggregate_daily(event_id, "payment.", since, until)

        return {
            "registrations": {
                "total": sum(r.count for r in reg_rows),
                "by_day": [{"date": str(r.date), "count": r.count} for r in reg_rows],
            },
            "revenue": {
                "total": float(sum(r.total_value for r in rev_rows)),
                "by_day": [{"date": str(r.date), "amount": float(r.total_value)} for r in rev_rows],
            },
        }
