"""Unit tests for GetGrowthAnalyticsUseCase."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest

from apps.intelligence.application.use_cases.get_growth_analytics import GetGrowthAnalyticsUseCase
from apps.intelligence.domain.entities import DailyAggregateEntity
from apps.intelligence.domain.repositories import IAnalyticsGrowthRepository


class FakeAnalyticsGrowthRepository(IAnalyticsGrowthRepository):
    """Returns pre-loaded daily aggregates for testing."""

    def __init__(self, data: dict[tuple[uuid.UUID, str], list[DailyAggregateEntity]] | None = None) -> None:
        self._data = data or {}

    def aggregate_daily(
        self,
        event_id: uuid.UUID,
        event_type_prefix: str,
        since: datetime | None,
        until: datetime | None,
    ) -> list[DailyAggregateEntity]:
        """Return pre-loaded aggregates for the given key."""
        return self._data.get((event_id, event_type_prefix), [])


def test_growth_analytics_returns_registration_counts() -> None:
    """Registration daily aggregates are returned correctly."""
    event_id = uuid.uuid4()
    reg_data = [
        DailyAggregateEntity(date=date(2024, 1, 1), count=10, total_value=Decimal("0")),
        DailyAggregateEntity(date=date(2024, 1, 2), count=20, total_value=Decimal("0")),
    ]
    repo = FakeAnalyticsGrowthRepository({(event_id, "registration."): reg_data})
    use_case = GetGrowthAnalyticsUseCase(repo)

    result = use_case.execute(event_id=event_id)

    assert result["registrations"]["total"] == 30
    assert len(result["registrations"]["by_day"]) == 2


def test_growth_analytics_returns_revenue_totals() -> None:
    """Revenue daily aggregates are summed correctly."""
    event_id = uuid.uuid4()
    rev_data = [
        DailyAggregateEntity(date=date(2024, 1, 1), count=5, total_value=Decimal("500.00")),
        DailyAggregateEntity(date=date(2024, 1, 2), count=3, total_value=Decimal("300.00")),
    ]
    repo = FakeAnalyticsGrowthRepository({(event_id, "payment."): rev_data})
    use_case = GetGrowthAnalyticsUseCase(repo)

    result = use_case.execute(event_id=event_id)

    assert result["revenue"]["total"] == pytest.approx(800.00)
    assert len(result["revenue"]["by_day"]) == 2


def test_growth_analytics_returns_zeros_when_no_events() -> None:
    """Empty event history yields zeros with no crash."""
    event_id = uuid.uuid4()
    repo = FakeAnalyticsGrowthRepository()
    use_case = GetGrowthAnalyticsUseCase(repo)

    result = use_case.execute(event_id=event_id)

    assert result["registrations"]["total"] == 0
    assert result["revenue"]["total"] == pytest.approx(0.0)
    assert result["registrations"]["by_day"] == []
    assert result["revenue"]["by_day"] == []
