"""Use case: retrieve the latest health score for an event."""

from __future__ import annotations

import uuid

from apps.intelligence.domain.entities import HealthScoreEntity
from apps.intelligence.domain.repositories import IHealthScoreRepository


class GetLatestHealthScoreUseCase:
    """Return the most recently calculated health score for an event."""

    def __init__(self, repo: IHealthScoreRepository) -> None:
        self._repo = repo

    def execute(self, *, event_id: uuid.UUID) -> HealthScoreEntity:
        """Return the latest score or raise HealthScoreNotFoundError if none exist."""
        return self._repo.get_latest_by_event(event_id)
