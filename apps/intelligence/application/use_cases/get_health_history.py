"""Use case: retrieve health ping history for dashboard display."""

from __future__ import annotations

from datetime import datetime

from apps.intelligence.domain.entities import HealthPingEntity
from apps.intelligence.domain.repositories import IHealthPingRepository


class GetHealthHistoryUseCase:
    """Query stored health pings with optional filters."""

    def __init__(self, repo: IHealthPingRepository) -> None:
        self._repo = repo

    def execute(
        self,
        *,
        service_name: str | None = None,
        since: datetime | None = None,
    ) -> list[HealthPingEntity]:
        """Return ping records filtered by service and/or time."""
        return self._repo.get_history(service_name=service_name, since=since)


class GetLatestHealthRoundUseCase:
    """Return the most recent ping for every service."""

    def __init__(self, repo: IHealthPingRepository) -> None:
        self._repo = repo

    def execute(self) -> list[HealthPingEntity]:
        """Return last ping per service."""
        return self._repo.get_latest_round()
