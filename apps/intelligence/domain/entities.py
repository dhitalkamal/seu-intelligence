"""Pure Python domain entities for the intelligence module with no framework dependencies."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(slots=True)
class AnalyticsEventEntity:
    """A single append-only analytics event record."""

    id: uuid.UUID
    event_type: str
    source_service: str
    occurred_at: datetime
    created_at: datetime
    event_id: uuid.UUID | None = None
    organisation_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    value: Decimal | None = None
    payload: dict = field(default_factory=dict)


@dataclass(slots=True)
class AttendeeMatchEntity:
    """A pairwise attendee match record for a specific event."""

    id: uuid.UUID
    event_id: uuid.UUID
    user_id_a: uuid.UUID
    user_id_b: uuid.UUID
    match_score: Decimal
    is_introduced: bool
    created_at: datetime
    match_signals: dict = field(default_factory=dict)
    introduced_at: datetime | None = None


@dataclass(slots=True)
class ConnectionPrivacyEntity:
    """A user's opt-in preference for the Who to Meet feature at a specific event."""

    id: uuid.UUID
    user_id: uuid.UUID
    event_id: uuid.UUID
    opted_in: bool
    created_at: datetime


@dataclass(slots=True)
class HealthScoreEntity:
    """A single calculated health score snapshot for an event."""

    id: uuid.UUID
    event_id: uuid.UUID
    score: int
    level: str
    calculated_at: datetime
    registration_velocity: Decimal = Decimal("0")
    conversion_rate: Decimal = Decimal("0")
    revenue_progress: Decimal = Decimal("0")
    predicted_attendance: int = 0
    risk_flags: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)
