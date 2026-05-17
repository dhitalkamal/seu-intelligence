"""DRF serializers for intelligence request deserialization and response shaping."""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers


class IngestEventSerializer(serializers.Serializer):
    """Payload for a single analytics event."""

    event_type = serializers.CharField(max_length=50)
    source_service = serializers.CharField(max_length=50)
    occurred_at = serializers.DateTimeField()
    event_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    organisation_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    user_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    value = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, default=None
    )
    payload = serializers.JSONField(required=False, default=dict)


class HealthScoreInputSerializer(serializers.Serializer):
    """Payload for calculating an event health score."""

    registration_velocity = serializers.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0")
    )
    conversion_rate = serializers.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    revenue_progress = serializers.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0")
    )
    capacity = serializers.IntegerField(min_value=0)
    registered_count = serializers.IntegerField(min_value=0)


class HealthScoreResponseSerializer(serializers.Serializer):
    """Public shape of a health score resource."""

    id = serializers.UUIDField()
    event_id = serializers.UUIDField()
    score = serializers.IntegerField()
    level = serializers.CharField()
    registration_velocity = serializers.DecimalField(max_digits=5, decimal_places=2)
    conversion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    revenue_progress = serializers.DecimalField(max_digits=5, decimal_places=2)
    predicted_attendance = serializers.IntegerField()
    risk_flags = serializers.ListField(child=serializers.CharField())
    recommendations = serializers.ListField(child=serializers.CharField())
    calculated_at = serializers.DateTimeField()
