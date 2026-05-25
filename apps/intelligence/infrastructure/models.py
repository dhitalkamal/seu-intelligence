"""Django ORM models for the intelligence domain. Maps to the intelligence schema."""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import models

from apps.intelligence.domain.entities import (
    AnalyticsEventEntity,
    AttendeeMatchEntity,
    ConnectionPrivacyEntity,
    HealthPingEntity,
    HealthScoreEntity,
)


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
                fields=["organization_id", "-occurred_at"],
                name="idx_analytics_org",
            ),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(null=True, blank=True)
    organization_id = models.UUIDField(null=True, blank=True)
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
            organization_id=self.organization_id,
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
            organization_id=entity.organization_id,
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
    registration_velocity = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
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


class AttendeeMatch(models.Model):
    """Pairwise attendee match record from the Who to Meet feature."""

    class Meta:
        db_table = '"intelligence"."attendee_match"'
        constraints = [
            models.UniqueConstraint(
                fields=["event_id", "user_id_a", "user_id_b"],
                name="unique_attendee_match",
            )
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField()
    user_id_a = models.UUIDField()
    user_id_b = models.UUIDField()
    match_score = models.DecimalField(max_digits=5, decimal_places=4)
    match_signals = models.JSONField(default=dict)
    is_introduced = models.BooleanField(default=False)
    introduced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def to_entity(self) -> AttendeeMatchEntity:
        """Map this ORM row to a pure-Python AttendeeMatchEntity."""
        return AttendeeMatchEntity(
            id=self.id,
            event_id=self.event_id,
            user_id_a=self.user_id_a,
            user_id_b=self.user_id_b,
            match_score=self.match_score,
            match_signals=self.match_signals or {},
            is_introduced=self.is_introduced,
            introduced_at=self.introduced_at,
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, entity: AttendeeMatchEntity) -> "AttendeeMatch":
        """Build an unsaved ORM instance from an AttendeeMatchEntity."""
        return cls(
            id=entity.id,
            event_id=entity.event_id,
            user_id_a=entity.user_id_a,
            user_id_b=entity.user_id_b,
            match_score=entity.match_score,
            match_signals=entity.match_signals,
            is_introduced=entity.is_introduced,
            introduced_at=entity.introduced_at,
        )


class ConnectionPrivacy(models.Model):
    """User opt-in preference for Who to Meet at a specific event."""

    class Meta:
        db_table = '"intelligence"."connection_privacy"'
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "event_id"],
                name="unique_connection_privacy",
            )
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    event_id = models.UUIDField()
    opted_in = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def to_entity(self) -> ConnectionPrivacyEntity:
        """Map this ORM row to a pure-Python ConnectionPrivacyEntity."""
        return ConnectionPrivacyEntity(
            id=self.id,
            user_id=self.user_id,
            event_id=self.event_id,
            opted_in=self.opted_in,
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, entity: ConnectionPrivacyEntity) -> "ConnectionPrivacy":
        """Build an unsaved ORM instance from a ConnectionPrivacyEntity."""
        return cls(
            id=entity.id,
            user_id=entity.user_id,
            event_id=entity.event_id,
            opted_in=entity.opted_in,
        )


class HealthPing(models.Model):
    """A single health check result for a service or infra dependency."""

    class Meta:
        db_table = '"intelligence"."health_ping"'
        indexes = [
            models.Index(
                fields=["service_name", "-checked_at"],
                name="idx_health_ping_service",
            ),
            models.Index(
                fields=["-checked_at"],
                name="idx_health_ping_time",
            ),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_name = models.CharField(max_length=50)
    service_type = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    latency_ms = models.IntegerField()
    details = models.JSONField(default=dict)
    checked_at = models.DateTimeField()

    def to_entity(self) -> HealthPingEntity:
        """Map this ORM row to a pure-Python HealthPingEntity."""
        return HealthPingEntity(
            id=self.id,
            service_name=self.service_name,
            service_type=self.service_type,
            status=self.status,
            latency_ms=self.latency_ms,
            details=self.details or {},
            checked_at=self.checked_at,
        )

    @classmethod
    def from_entity(cls, entity: HealthPingEntity) -> "HealthPing":
        """Build an unsaved ORM instance from a HealthPingEntity."""
        return cls(
            id=entity.id,
            service_name=entity.service_name,
            service_type=entity.service_type,
            status=entity.status,
            latency_ms=entity.latency_ms,
            details=entity.details,
            checked_at=entity.checked_at,
        )
