"""Hand-rolled in-memory fakes for intelligence repository interfaces."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from apps.intelligence.domain.entities import AnalyticsEventEntity, HealthScoreEntity
from apps.intelligence.domain.exceptions import HealthScoreNotFoundError
from apps.intelligence.domain.repositories import IAnalyticsEventRepository, IHealthScoreRepository


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_event(**kwargs: object) -> AnalyticsEventEntity:
    """Build an AnalyticsEventEntity with sensible defaults for testing."""
    now = _now()
    defaults: dict = {
        "id": uuid.uuid4(),
        "event_type": "registration.created",
        "source_service": "participation-service",
        "occurred_at": now,
        "created_at": now,
        "event_id": None,
        "organisation_id": None,
        "user_id": None,
        "value": None,
        "payload": {},
    }
    defaults.update(kwargs)
    return AnalyticsEventEntity(**defaults)  # type: ignore[arg-type]


class FakeAnalyticsEventRepository(IAnalyticsEventRepository):
    """In-memory append-only analytics event store."""

    def __init__(self) -> None:
        self._store: list[AnalyticsEventEntity] = []

    def create(self, entity: AnalyticsEventEntity) -> AnalyticsEventEntity:
        """Append and return the entity."""
        self._store.append(entity)
        return entity

    def bulk_create(self, entities: list[AnalyticsEventEntity]) -> int:
        """Append all entities and return count."""
        self._store.extend(entities)
        return len(entities)


class FakeHealthScoreRepository(IHealthScoreRepository):
    """In-memory append-only health score store."""

    def __init__(self) -> None:
        self._store: list[HealthScoreEntity] = []

    def create(self, entity: HealthScoreEntity) -> HealthScoreEntity:
        """Append and return the entity."""
        self._store.append(entity)
        return entity

    def get_latest_by_event(self, event_id: uuid.UUID) -> HealthScoreEntity:
        """Return the most recently calculated score or raise HealthScoreNotFoundError."""
        matches = [s for s in self._store if s.event_id == event_id]
        if not matches:
            raise HealthScoreNotFoundError("No health score found for this event.")
        return sorted(matches, key=lambda s: s.calculated_at, reverse=True)[0]
