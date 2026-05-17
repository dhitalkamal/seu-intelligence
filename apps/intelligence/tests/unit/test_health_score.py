"""Unit tests for CalculateHealthScoreUseCase and GetLatestHealthScoreUseCase."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from apps.intelligence.application.use_cases.calculate_health import (
    CalculateHealthScoreUseCase,
    _classify_level,
)
from apps.intelligence.application.use_cases.get_health import GetLatestHealthScoreUseCase
from apps.intelligence.domain.exceptions import HealthScoreNotFoundError
from apps.intelligence.tests.unit.fakes import FakeHealthScoreRepository


def _uc() -> CalculateHealthScoreUseCase:
    return CalculateHealthScoreUseCase(FakeHealthScoreRepository())


def test_score_formula_correct():
    """fill_rate=0.8, conversion=0.7, velocity=0.5, revenue=0.6 gives score=69 and level=healthy."""
    result = _uc().execute(
        event_id=uuid.uuid4(),
        registration_velocity=Decimal("0.5"),
        conversion_rate=Decimal("0.7"),
        revenue_progress=Decimal("0.6"),
        capacity=100,
        registered_count=80,
    )
    assert result.score == 69
    assert result.level == "healthy"


def test_score_capacity_zero_returns_zero():
    """capacity=0 guard sets fill_rate=0, resulting in score=0 and level=critical."""
    result = _uc().execute(
        event_id=uuid.uuid4(),
        registration_velocity=Decimal("0"),
        conversion_rate=Decimal("0"),
        revenue_progress=Decimal("0"),
        capacity=0,
        registered_count=0,
    )
    assert result.score == 0
    assert result.level == "critical"


def test_level_thresholds():
    """All five level classifications return the correct label."""
    assert _classify_level(80) == "excellent"
    assert _classify_level(60) == "healthy"
    assert _classify_level(40) == "moderate"
    assert _classify_level(20) == "at_risk"
    assert _classify_level(19) == "critical"


def test_risk_flags_low_fill_rate():
    """fill_rate below 0.3 adds low_fill_rate flag and at least one recommendation."""
    result = _uc().execute(
        event_id=uuid.uuid4(),
        registration_velocity=Decimal("0.5"),
        conversion_rate=Decimal("0.5"),
        revenue_progress=Decimal("0.5"),
        capacity=100,
        registered_count=10,
    )
    assert "low_fill_rate" in result.risk_flags
    assert len(result.recommendations) > 0


def test_get_latest_raises_when_none():
    """HealthScoreNotFoundError raised when no score exists for the event."""
    repo = FakeHealthScoreRepository()
    with pytest.raises(HealthScoreNotFoundError):
        GetLatestHealthScoreUseCase(repo).execute(event_id=uuid.uuid4())
