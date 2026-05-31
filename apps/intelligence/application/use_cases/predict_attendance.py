"""Use case: predict final attendance for an event from registration trends."""

from __future__ import annotations

import math
import uuid
from datetime import datetime

from apps.intelligence.domain.repositories import IAnalyticsGrowthRepository

_NO_SHOW_RATE = 0.15


def _confidence(day_count: int) -> str:
    """Map number of days with data to a confidence label."""
    if day_count >= 8:
        return "high"
    if day_count >= 3:
        return "medium"
    return "low"


class PredictAttendanceUseCase:
    """Estimate how many attendees will show up based on registration analytics."""

    def __init__(self, growth_repo: IAnalyticsGrowthRepository) -> None:
        self._growth_repo = growth_repo

    def execute(
        self,
        *,
        event_id: uuid.UUID,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> dict:
        """
        Return a prediction dict with:
          registered_count, predicted_attendance, no_show_rate, confidence.
        """
        rows = self._growth_repo.aggregate_daily(event_id, "registration.", since, until)
        registered_count = sum(r.count for r in rows)
        predicted = math.floor(registered_count * (1 - _NO_SHOW_RATE))
        return {
            "registered_count": registered_count,
            "predicted_attendance": predicted,
            "no_show_rate": _NO_SHOW_RATE,
            "confidence": _confidence(len(rows)),
        }
