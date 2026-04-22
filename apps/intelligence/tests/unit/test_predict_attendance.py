"""Unit tests for PredictAttendanceUseCase."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest

from apps.intelligence.application.use_cases.predict_attendance import PredictAttendanceUseCase
from apps.intelligence.domain.entities import DailyAggregateEntity
from apps.intelligence.domain.repositories import IAnalyticsGrowthRepository


class FakeGrowthRepo(IAnalyticsGrowthRepository):
    """Returns pre-loaded daily aggregates."""

    def __init__(self, data: list[DailyAggregateEntity]) -> None:
        self._data = data

    def aggregate_daily(
        self,
        event_id: uuid.UUID,
        event_type_prefix: str,
        since: datetime | None,
        until: datetime | None,
    ) -> list[DailyAggregateEntity]:
        """Return all pre-loaded data regardless of prefix."""
        return self._data


def test_predict_attendance_returns_registered_count() -> None:
    """Total registrations are summed correctly from daily rows."""
    event_id = uuid.uuid4()
    repo = FakeGrowthRepo(
        [
            DailyAggregateEntity(date=date(2024, 1, 1), count=10, total_value=Decimal("0")),
            DailyAggregateEntity(date=date(2024, 1, 2), count=20, total_value=Decimal("0")),
        ]
    )
    result = PredictAttendanceUseCase(repo).execute(event_id=event_id)

    assert result["registered_count"] == 30


def test_predict_attendance_applies_no_show_rate() -> None:
    """Predicted attendance is registered_count * show_up_rate."""
    event_id = uuid.uuid4()
    repo = FakeGrowthRepo(
        [
            DailyAggregateEntity(date=date(2024, 1, 1), count=100, total_value=Decimal("0")),
        ]
    )
    result = PredictAttendanceUseCase(repo).execute(event_id=event_id)

    # default no-show rate is 15% -> predicted = floor(100 * 0.85) = 85
    assert result["predicted_attendance"] == 85
    assert result["no_show_rate"] == pytest.approx(0.15)


def test_predict_attendance_confidence_low_with_few_data_points() -> None:
    """Confidence is low when fewer than 3 days of data exist."""
    event_id = uuid.uuid4()
    repo = FakeGrowthRepo(
        [
            DailyAggregateEntity(date=date(2024, 1, 1), count=5, total_value=Decimal("0")),
        ]
    )
    result = PredictAttendanceUseCase(repo).execute(event_id=event_id)

    assert result["confidence"] == "low"


def test_predict_attendance_confidence_medium_with_moderate_data() -> None:
    """Confidence is medium for 3-7 days of data."""
    event_id = uuid.uuid4()
    rows = [DailyAggregateEntity(date=date(2024, 1, i), count=10, total_value=Decimal("0")) for i in range(1, 5)]
    result = PredictAttendanceUseCase(FakeGrowthRepo(rows)).execute(event_id=event_id)

    assert result["confidence"] == "medium"


def test_predict_attendance_confidence_high_with_rich_data() -> None:
    """Confidence is high when more than 7 days of data are available."""
    event_id = uuid.uuid4()
    rows = [DailyAggregateEntity(date=date(2024, 1, i), count=10, total_value=Decimal("0")) for i in range(1, 10)]
    result = PredictAttendanceUseCase(FakeGrowthRepo(rows)).execute(event_id=event_id)

    assert result["confidence"] == "high"


def test_predict_attendance_zero_registrations() -> None:
    """Zero registrations results in zero predicted attendance."""
    event_id = uuid.uuid4()
    repo = FakeGrowthRepo([])
    result = PredictAttendanceUseCase(repo).execute(event_id=event_id)

    assert result["registered_count"] == 0
    assert result["predicted_attendance"] == 0
    assert result["confidence"] == "low"
