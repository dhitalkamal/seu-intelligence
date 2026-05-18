"""Concrete repository implementations backed by the Django ORM."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from apps.intelligence.domain.entities import (
    AnalyticsEventEntity,
    AttendeeMatchEntity,
    ConnectionPrivacyEntity,
    HealthScoreEntity,
)
from apps.intelligence.domain.exceptions import HealthScoreNotFoundError, MatchNotFoundError
from apps.intelligence.domain.repositories import (
    IAnalyticsEventQueryRepository,
    IAnalyticsEventRepository,
    IAttendeeMatchRepository,
    IConnectionPrivacyRepository,
    IHealthScoreRepository,
)
from apps.intelligence.infrastructure.models import (
    AnalyticsEvent,
    AttendeeMatch,
    ConnectionPrivacy,
    EventHealthScore,
)


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


class DjangoAttendeeMatchRepository(IAttendeeMatchRepository):
    """Persists AttendeeMatch entities using the Django ORM."""

    def get_matches_for_user(
        self, event_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[AttendeeMatchEntity]:
        """Return all match records where the user appears on either side."""
        from django.db.models import Q

        qs = AttendeeMatch.objects.filter(
            Q(user_id_a=user_id) | Q(user_id_b=user_id), event_id=event_id
        ).order_by("-match_score")
        return [obj.to_entity() for obj in qs]

    def get_pair(
        self, event_id: uuid.UUID, user_id_a: uuid.UUID, user_id_b: uuid.UUID
    ) -> AttendeeMatchEntity | None:
        """Return the match between two users or None."""
        from django.db.models import Q

        obj = (
            AttendeeMatch.objects.filter(event_id=event_id)
            .filter(
                Q(user_id_a=user_id_a, user_id_b=user_id_b)
                | Q(user_id_a=user_id_b, user_id_b=user_id_a)
            )
            .first()
        )
        return obj.to_entity() if obj else None

    def bulk_create(self, entities: list[AttendeeMatchEntity]) -> None:
        """Batch-insert match records, ignoring conflicts."""
        objs = [AttendeeMatch.from_entity(e) for e in entities]
        AttendeeMatch.objects.bulk_create(objs, ignore_conflicts=True)

    def mark_introduced(self, match_id: uuid.UUID) -> AttendeeMatchEntity:
        """Set is_introduced=True and record introduced_at timestamp."""
        try:
            obj = AttendeeMatch.objects.get(id=match_id)
        except AttendeeMatch.DoesNotExist:
            raise MatchNotFoundError(f"Match {match_id} not found.")
        obj.is_introduced = True
        obj.introduced_at = datetime.now(timezone.utc)
        obj.save(update_fields=["is_introduced", "introduced_at"])
        return obj.to_entity()

    def list_user_ids_for_event(self, event_id: uuid.UUID) -> list[uuid.UUID]:
        """Return distinct user_ids registered at this event via analytics events."""
        ids = (
            AnalyticsEvent.objects.filter(event_id=event_id, user_id__isnull=False)
            .values_list("user_id", flat=True)
            .distinct()
        )
        return list(ids)


class DjangoConnectionPrivacyRepository(IConnectionPrivacyRepository):
    """Persists ConnectionPrivacy preferences using the Django ORM."""

    def get_or_create(self, user_id: uuid.UUID, event_id: uuid.UUID) -> ConnectionPrivacyEntity:
        """Return existing preference or create a default opted_in=False one."""
        import uuid as _uuid

        obj, _ = ConnectionPrivacy.objects.get_or_create(
            user_id=user_id,
            event_id=event_id,
            defaults={"id": _uuid.uuid4(), "opted_in": False},
        )
        return obj.to_entity()

    def upsert(self, entity: ConnectionPrivacyEntity) -> ConnectionPrivacyEntity:
        """Persist updated preference."""
        ConnectionPrivacy.objects.filter(user_id=entity.user_id, event_id=entity.event_id).update(
            opted_in=entity.opted_in
        )
        return entity


class DjangoAnalyticsEventQueryRepository(IAnalyticsEventQueryRepository):
    """Read-only analytics queries for match-signal computation."""

    def get_event_ids_for_user(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        """Return all event_ids the user appeared in across analytics events."""
        ids = (
            AnalyticsEvent.objects.filter(user_id=user_id, event_id__isnull=False)
            .values_list("event_id", flat=True)
            .distinct()
        )
        return list(ids)
