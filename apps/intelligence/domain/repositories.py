"""Abstract repository interfaces for the intelligence module."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

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


class IAnalyticsEventRepository(ABC):
    """Persistence contract for append-only analytics events."""

    @abstractmethod
    def create(self, entity: AnalyticsEventEntity) -> AnalyticsEventEntity: ...

    @abstractmethod
    def bulk_create(self, entities: list[AnalyticsEventEntity]) -> int: ...


class IAttendeeMatchRepository(ABC):
    """Persistence contract for attendee match records."""

    @abstractmethod
    def get_matches_for_user(self, event_id: uuid.UUID, user_id: uuid.UUID) -> list[AttendeeMatchEntity]: ...

    @abstractmethod
    def get_pair(self, event_id: uuid.UUID, user_id_a: uuid.UUID, user_id_b: uuid.UUID) -> AttendeeMatchEntity | None: ...

    @abstractmethod
    def bulk_create(self, entities: list[AttendeeMatchEntity]) -> None: ...

    @abstractmethod
    def mark_introduced(self, match_id: uuid.UUID) -> AttendeeMatchEntity: ...

    @abstractmethod
    def list_user_ids_for_event(self, event_id: uuid.UUID) -> list[uuid.UUID]: ...


class IConnectionPrivacyRepository(ABC):
    """Persistence contract for user opt-in preferences."""

    @abstractmethod
    def get_or_create(self, user_id: uuid.UUID, event_id: uuid.UUID) -> ConnectionPrivacyEntity: ...

    @abstractmethod
    def upsert(self, entity: ConnectionPrivacyEntity) -> ConnectionPrivacyEntity: ...


class IAnalyticsEventQueryRepository(ABC):
    """Read-only queries over analytics events for match computation."""

    @abstractmethod
    def get_event_ids_for_user(self, user_id: uuid.UUID) -> list[uuid.UUID]: ...


class IHealthScoreRepository(ABC):
    """Persistence contract for append-only health score records."""

    @abstractmethod
    def create(self, entity: HealthScoreEntity) -> HealthScoreEntity: ...

    @abstractmethod
    def get_latest_by_event(self, event_id: uuid.UUID) -> HealthScoreEntity: ...


class IHealthPingRepository(ABC):
    """Persistence contract for service health ping records."""

    @abstractmethod
    def bulk_create(self, entities: list[HealthPingEntity]) -> int: ...

    @abstractmethod
    def get_history(
        self,
        *,
        service_name: str | None = None,
        since: datetime | None = None,
    ) -> list[HealthPingEntity]: ...

    @abstractmethod
    def get_latest_round(self) -> list[HealthPingEntity]: ...

    @abstractmethod
    def delete_older_than(self, cutoff: datetime) -> int: ...


class IReportJobRepository(ABC):
    """Persistence contract for report generation jobs."""

    @abstractmethod
    def create(self, entity: ReportJobEntity) -> ReportJobEntity: ...

    @abstractmethod
    def get_by_id(self, job_id: uuid.UUID) -> ReportJobEntity: ...

    @abstractmethod
    def update(self, entity: ReportJobEntity) -> ReportJobEntity: ...


class IReportStorage(ABC):
    """Storage abstraction for generating presigned download URLs."""

    @abstractmethod
    def upload(self, file_key: str, content: bytes, content_type: str) -> None: ...

    @abstractmethod
    def generate_presigned_url(self, file_key: str, expires_in: int = 3600) -> str: ...


class IAnalyticsGrowthRepository(ABC):
    """Read-only queries that aggregate analytics events into daily buckets."""

    @abstractmethod
    def aggregate_daily(
        self,
        event_id: uuid.UUID,
        event_type_prefix: str,
        since: datetime | None,
        until: datetime | None,
    ) -> list[DailyAggregateEntity]:
        """Return one DailyAggregateEntity per day within the date range."""
        ...


class IScheduledReportRepository(ABC):
    """Persistence contract for recurring report schedule configurations."""

    @abstractmethod
    def create(self, entity: ScheduledReportEntity) -> ScheduledReportEntity: ...

    @abstractmethod
    def list_due(self, as_of: datetime) -> list[ScheduledReportEntity]:
        """Return active schedules whose next_run_at is on or before as_of."""
        ...

    @abstractmethod
    def update(self, entity: ScheduledReportEntity) -> ScheduledReportEntity: ...

    @abstractmethod
    def list_for_event(self, event_id: uuid.UUID) -> list[ScheduledReportEntity]: ...

    @abstractmethod
    def deactivate(self, schedule_id: uuid.UUID) -> ScheduledReportEntity: ...
