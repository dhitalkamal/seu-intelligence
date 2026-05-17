"""Use case: calculate and persist an event health score."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from apps.intelligence.domain.entities import HealthScoreEntity
from apps.intelligence.domain.repositories import IHealthScoreRepository


def _classify_level(score: int) -> str:
    """Map a clamped 0-100 score to a named level."""
    if score >= 80:
        return "excellent"
    if score >= 60:
        return "healthy"
    if score >= 40:
        return "moderate"
    if score >= 20:
        return "at_risk"
    return "critical"


def _clamp(value: float) -> int:
    """Clamp a float to the integer range 0-100."""
    return int(max(0.0, min(100.0, value)))


class CalculateHealthScoreUseCase:
    """Compute the health score for an event and persist it as a new record."""

    def __init__(self, repo: IHealthScoreRepository) -> None:
        self._repo = repo

    def execute(
        self,
        *,
        event_id: uuid.UUID,
        registration_velocity: Decimal,
        conversion_rate: Decimal,
        revenue_progress: Decimal,
        capacity: int,
        registered_count: int,
    ) -> HealthScoreEntity:
        """
        Apply the health score formula and flag risks.

        Formula: (fill_rate x 40) + (conversion_rate x 30) + (velocity x 20) + (revenue x 10)

        @returns the persisted HealthScoreEntity
        """
        fill_rate = Decimal(registered_count) / Decimal(capacity) if capacity > 0 else Decimal("0")

        raw = (
            float(fill_rate) * 40
            + float(conversion_rate) * 30
            + float(registration_velocity) * 20
            + float(revenue_progress) * 10
        )
        score = _clamp(raw)
        level = _classify_level(score)

        risk_flags: list[str] = []
        recommendations: list[str] = []

        if fill_rate < Decimal("0.3"):
            risk_flags.append("low_fill_rate")
            recommendations.append("Increase event promotion to attract more registrations.")
        if registration_velocity < Decimal("0.3"):
            risk_flags.append("slow_velocity")
            recommendations.append("Run a limited-time discount to accelerate registrations.")
        if conversion_rate < Decimal("0.3"):
            risk_flags.append("low_conversion")
            recommendations.append("Review the event page and registration flow for friction.")

        entity = HealthScoreEntity(
            id=uuid.uuid4(),
            event_id=event_id,
            score=score,
            level=level,
            registration_velocity=registration_velocity,
            conversion_rate=conversion_rate,
            revenue_progress=revenue_progress,
            predicted_attendance=int(float(fill_rate) * capacity),
            risk_flags=risk_flags,
            recommendations=recommendations,
            calculated_at=datetime.now(timezone.utc),
        )
        return self._repo.create(entity)
