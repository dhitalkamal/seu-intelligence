"""Django ORM models for the intelligence domain. Maps to the intelligence schema."""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import models

from apps.intelligence.domain.entities import AnalyticsEventEntity, HealthScoreEntity


class AnalyticsEvent(models.Model):
    """Append-only analytics event record."""

    class Meta:
        db_table = '"intelligence"."analytics_event"'
        indexes = [
            models.Index(
                fields=["event_id", "event_type", "-occurred_at"],
                name="idx_analytics_event_event",
            ),
            models.Index(
                fields=["organisation_id", "-occurred_at"],
                name="idx_analytics_org",
            ),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(null=True, blank=True)
    organisation_id = models.UUIDField(null=True, blank=True)
    user_id = models.UUIDField(null=True, blank=True)
    event_type = models.CharField(max_length=50)
    value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    payload = models.JSONField(default=dict)
    source_service = models.CharField(max_length=50)
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def to_entity(self) -> AnalyticsEventEntity:
        """Map this ORM row to a pure-Python AnalyticsEventEntity."""
        return AnalyticsEventEntity(
            id=self.id,
            event_type=self.event_type,
            source_service=self.source_service,
            occurred_at=self.occurred_at,
            created_at=self.created_at,
            event_id=self.event_id,
            organisation_id=self.organisation_id,
            user_id=self.user_id,
            value=self.value,
            payload=self.payload,
        )

    @classmethod
    def from_entity(cls, entity: AnalyticsEventEntity) -> "AnalyticsEvent":
        """Build an unsaved ORM instance from an AnalyticsEventEntity."""
        return cls(
            id=entity.id,
            event_type=entity.event_type,
            source_service=entity.source_service,
            occurred_at=entity.occurred_at,
            event_id=entity.event_id,
            organisation_id=entity.organisation_id,
            user_id=entity.user_id,
            value=entity.value,
            payload=entity.payload,
        )


class EventHealthScore(models.Model):
    """Append-only health score snapshot for an event."""

    class Meta:
        db_table = '"intelligence"."event_health_score"'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField()
    score = models.SmallIntegerField()
    level = models.CharField(max_length=20)
    registration_velocity = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0")
    )
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    revenue_progress = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    predicted_attendance = models.IntegerField(default=0)
    risk_flags = models.JSONField(default=list)
    recommendations = models.JSONField(default=list)
    calculated_at = models.DateTimeField(auto_now_add=True)

    def to_entity(self) -> HealthScoreEntity:
        """Map this ORM row to a pure-Python HealthScoreEntity."""
        return HealthScoreEntity(
            id=self.id,
            event_id=self.event_id,
            score=self.score,
            level=self.level,
            calculated_at=self.calculated_at,
            registration_velocity=self.registration_velocity,
            conversion_rate=self.conversion_rate,
            revenue_progress=self.revenue_progress,
            predicted_attendance=self.predicted_attendance,
            risk_flags=self.risk_flags,
            recommendations=self.recommendations,
        )

    @classmethod
    def from_entity(cls, entity: HealthScoreEntity) -> "EventHealthScore":
        """Build an unsaved ORM instance from a HealthScoreEntity."""
        return cls(
            id=entity.id,
            event_id=entity.event_id,
            score=entity.score,
            level=entity.level,
            registration_velocity=entity.registration_velocity,
            conversion_rate=entity.conversion_rate,
            revenue_progress=entity.revenue_progress,
            predicted_attendance=entity.predicted_attendance,
            risk_flags=entity.risk_flags,
            recommendations=entity.recommendations,
        )
