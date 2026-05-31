"""Concrete repository implementations backed by the Django ORM."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from apps.intelligence.domain.entities import (
    AnalyticsEventEntity,
    AttendeeMatchEntity,
    ConnectionPrivacyEntity,
    DailyAggregateEntity,
    HealthPingEntity,
    HealthScoreEntity,
    ReportJobEntity,
    ScheduledReportEntity,
)
from apps.intelligence.domain.exceptions import (
    HealthScoreNotFoundError,
    MatchNotFoundError,
    ReportJobNotFoundError,
    ScheduledReportNotFoundError,
)
from apps.intelligence.domain.repositories import (
    IAnalyticsEventQueryRepository,
    IAnalyticsEventRepository,
    IAnalyticsGrowthRepository,
    IAttendeeMatchRepository,
    IConnectionPrivacyRepository,
    IHealthPingRepository,
    IHealthScoreRepository,
    IReportJobRepository,
    IScheduledReportRepository,
)
from apps.intelligence.infrastructure.models import (
    AnalyticsEvent,
    AttendeeMatch,
    ConnectionPrivacy,
    EventHealthScore,
    HealthPing,
    ReportJob,
    ScheduledReport,
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

    def get_matches_for_user(self, event_id: uuid.UUID, user_id: uuid.UUID) -> list[AttendeeMatchEntity]:
        """Return all match records where the user appears on either side."""
        from django.db.models import Q

        qs = AttendeeMatch.objects.filter(Q(user_id_a=user_id) | Q(user_id_b=user_id), event_id=event_id).order_by("-match_score")
        return [obj.to_entity() for obj in qs]

    def get_pair(self, event_id: uuid.UUID, user_id_a: uuid.UUID, user_id_b: uuid.UUID) -> AttendeeMatchEntity | None:
        """Return the match between two users or None."""
        from django.db.models import Q

        obj = (
            AttendeeMatch.objects.filter(event_id=event_id)
            .filter(Q(user_id_a=user_id_a, user_id_b=user_id_b) | Q(user_id_a=user_id_b, user_id_b=user_id_a))
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
        ids = AnalyticsEvent.objects.filter(event_id=event_id, user_id__isnull=False).values_list("user_id", flat=True).distinct()
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
        ConnectionPrivacy.objects.filter(user_id=entity.user_id, event_id=entity.event_id).update(opted_in=entity.opted_in)
        return entity


class DjangoAnalyticsEventQueryRepository(IAnalyticsEventQueryRepository):
    """Read-only analytics queries for match-signal computation."""

    def get_event_ids_for_user(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        """Return all event_ids the user appeared in across analytics events."""
        ids = AnalyticsEvent.objects.filter(user_id=user_id, event_id__isnull=False).values_list("event_id", flat=True).distinct()
        return list(ids)


class DjangoHealthPingRepository(IHealthPingRepository):
    """Persists HealthPing records using the Django ORM."""

    def bulk_create(self, entities: list[HealthPingEntity]) -> int:
        """Batch-insert ping results and return count."""
        objs = [HealthPing.from_entity(e) for e in entities]
        HealthPing.objects.bulk_create(objs)
        return len(objs)

    def get_history(
        self,
        *,
        service_name: str | None = None,
        since: datetime | None = None,
    ) -> list[HealthPingEntity]:
        """Return ping records filtered by service and/or time window."""
        qs = HealthPing.objects.all()
        if service_name:
            qs = qs.filter(service_name=service_name)
        if since:
            qs = qs.filter(checked_at__gte=since)
        return [obj.to_entity() for obj in qs.order_by("checked_at")]

    def get_latest_round(self) -> list[HealthPingEntity]:
        """Return the most recent ping for each service."""
        from django.db.models import Max

        latest_ts = HealthPing.objects.aggregate(latest=Max("checked_at"))["latest"]
        if latest_ts is None:
            return []
        qs = HealthPing.objects.filter(checked_at=latest_ts)
        return [obj.to_entity() for obj in qs]

    def delete_older_than(self, cutoff: datetime) -> int:
        """Remove all rows older than cutoff, return count deleted."""
        count, _ = HealthPing.objects.filter(checked_at__lt=cutoff).delete()
        return count


class DjangoReportJobRepository(IReportJobRepository):
    """Persists ReportJob entities using the Django ORM."""

    def create(self, entity: ReportJobEntity) -> ReportJobEntity:
        """Persist a new job and return it."""
        obj = ReportJob.from_entity(entity)
        obj.save(using="default")
        return obj.to_entity()

    def get_by_id(self, job_id: uuid.UUID) -> ReportJobEntity:
        """Return the job or raise ReportJobNotFoundError."""
        try:
            obj = ReportJob.objects.get(id=job_id)
        except ReportJob.DoesNotExist:
            raise ReportJobNotFoundError(f"Report job {job_id} not found.")
        return obj.to_entity()

    def update(self, entity: ReportJobEntity) -> ReportJobEntity:
        """Overwrite status, file_url, and completed_at on the stored row."""
        ReportJob.objects.filter(id=entity.id).update(
            status=entity.status,
            file_url=entity.file_url,
            completed_at=entity.completed_at,
        )
        return entity

    def list_by_user(self, user_id: uuid.UUID) -> list[ReportJobEntity]:
        """Return all report jobs requested by the user, newest first."""
        return [obj.to_entity() for obj in ReportJob.objects.filter(requested_by=user_id).order_by("-created_at")]


class DjangoAnalyticsGrowthRepository(IAnalyticsGrowthRepository):
    """Aggregates analytics events into daily registration and revenue buckets."""

    def aggregate_daily(
        self,
        event_id: uuid.UUID,
        event_type_prefix: str,
        since: datetime | None,
        until: datetime | None,
    ) -> list[DailyAggregateEntity]:
        """Return one DailyAggregateEntity per day matching the event_type prefix and date range."""
        from decimal import Decimal as _Decimal

        from django.db.models import Sum
        from django.db.models.functions import TruncDate

        qs = AnalyticsEvent.objects.filter(
            event_id=event_id,
            event_type__startswith=event_type_prefix,
        )
        if since is not None:
            qs = qs.filter(occurred_at__gte=since)
        if until is not None:
            qs = qs.filter(occurred_at__lte=until)

        from django.db.models import Count

        rows = qs.annotate(day=TruncDate("occurred_at")).values("day").annotate(count=Count("id"), total_value=Sum("value")).order_by("day")

        result = []
        for row in rows:
            result.append(
                DailyAggregateEntity(
                    date=row["day"],
                    count=row["count"],
                    total_value=row["total_value"] or _Decimal("0"),
                )
            )
        return result


class DjangoScheduledReportRepository(IScheduledReportRepository):
    """Persists ScheduledReport entities using the Django ORM."""

    def create(self, entity: ScheduledReportEntity) -> ScheduledReportEntity:
        """Persist a new schedule and return the saved entity."""
        obj = ScheduledReport.from_entity(entity)
        obj.save(using="default")
        return obj.to_entity()

    def list_due(self, as_of: datetime) -> list[ScheduledReportEntity]:
        """Return active schedules whose next_run_at is on or before as_of."""
        qs = ScheduledReport.objects.filter(is_active=True, next_run_at__lte=as_of)
        return [obj.to_entity() for obj in qs]

    def update(self, entity: ScheduledReportEntity) -> ScheduledReportEntity:
        """Overwrite is_active, next_run_at, and last_run_at on the stored row."""
        ScheduledReport.objects.filter(id=entity.id).update(
            is_active=entity.is_active,
            next_run_at=entity.next_run_at,
            last_run_at=entity.last_run_at,
        )
        return entity

    def list_for_event(self, event_id: uuid.UUID) -> list[ScheduledReportEntity]:
        """Return all schedules for a given event, newest first."""
        qs = ScheduledReport.objects.filter(event_id=event_id).order_by("-created_at")
        return [obj.to_entity() for obj in qs]

    def deactivate(self, schedule_id: uuid.UUID) -> ScheduledReportEntity:
        """Set is_active=False and return the updated entity."""
        try:
            obj = ScheduledReport.objects.get(id=schedule_id)
        except ScheduledReport.DoesNotExist:
            raise ScheduledReportNotFoundError(f"Scheduled report {schedule_id} not found.")
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        return obj.to_entity()
