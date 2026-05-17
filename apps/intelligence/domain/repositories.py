"""Abstract repository interfaces for the intelligence module."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.intelligence.domain.entities import AnalyticsEventEntity, HealthScoreEntity


class IAnalyticsEventRepository(ABC):
    """Persistence contract for append-only analytics events."""

    @abstractmethod
    def create(self, entity: AnalyticsEventEntity) -> AnalyticsEventEntity: ...

    @abstractmethod
    def bulk_create(self, entities: list[AnalyticsEventEntity]) -> int: ...


class IHealthScoreRepository(ABC):
    """Persistence contract for append-only health score records."""

    @abstractmethod
    def create(self, entity: HealthScoreEntity) -> HealthScoreEntity: ...

    @abstractmethod
    def get_latest_by_event(self, event_id: uuid.UUID) -> HealthScoreEntity: ...
