"""Concrete repository implementations backed by the Django ORM."""

from __future__ import annotations

import uuid

from apps.intelligence.domain.entities import AnalyticsEventEntity, HealthScoreEntity
from apps.intelligence.domain.exceptions import HealthScoreNotFoundError
from apps.intelligence.domain.repositories import IAnalyticsEventRepository, IHealthScoreRepository
from apps.intelligence.infrastructure.models import AnalyticsEvent, EventHealthScore


class DjangoAnalyticsEventRepository(IAnalyticsEventRepository):
    """Persists AnalyticsEvent entities using the Django ORM."""

    def create(self, entity: AnalyticsEventEntity) -> AnalyticsEventEntity:
        """Persist a single event and return it."""
        obj = AnalyticsEvent.from_entity(entity)
        obj.save(using="default")
        return obj.to_entity()

    def bulk_create(self, entities: list[AnalyticsEventEntity]) -> int:
        """Bulk-insert all events and return count."""
        objs = [AnalyticsEvent.from_entity(e) for e in entities]
        AnalyticsEvent.objects.bulk_create(objs)
        return len(objs)


class DjangoHealthScoreRepository(IHealthScoreRepository):
    """Persists EventHealthScore entities using the Django ORM."""

    def create(self, entity: HealthScoreEntity) -> HealthScoreEntity:
        """Persist a health score and return it."""
        obj = EventHealthScore.from_entity(entity)
        obj.save(using="default")
        return obj.to_entity()

    def get_latest_by_event(self, event_id: uuid.UUID) -> HealthScoreEntity:
        """Return the most recently created score or raise HealthScoreNotFoundError."""
        obj = EventHealthScore.objects.filter(event_id=event_id).order_by("-calculated_at").first()
        if obj is None:
            raise HealthScoreNotFoundError("No health score found for this event.")
        return obj.to_entity()
