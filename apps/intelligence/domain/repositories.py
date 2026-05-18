"""Abstract repository interfaces for the intelligence module."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.intelligence.domain.entities import (
    AnalyticsEventEntity,
    AttendeeMatchEntity,
    ConnectionPrivacyEntity,
    HealthScoreEntity,
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
    def get_matches_for_user(
        self, event_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[AttendeeMatchEntity]: ...

    @abstractmethod
    def get_pair(
        self, event_id: uuid.UUID, user_id_a: uuid.UUID, user_id_b: uuid.UUID
    ) -> AttendeeMatchEntity | None: ...

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
