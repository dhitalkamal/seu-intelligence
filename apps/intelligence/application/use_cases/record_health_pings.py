"""Use case: record a batch of health ping results."""

from __future__ import annotations

import uuid
from datetime import datetime

from apps.intelligence.domain.entities import HealthPingEntity
from apps.intelligence.domain.repositories import IHealthPingRepository


class RecordHealthPingsUseCase:
    """Persist a batch of health ping results from a single check round."""

    def __init__(self, repo: IHealthPingRepository) -> None:
        self._repo = repo

    def execute(
        self,
        *,
        pings: list[dict],
        checked_at: datetime,
    ) -> int:
        """Build entities from raw ping dicts and bulk-insert them. Returns count."""
        entities = [
            HealthPingEntity(
                id=uuid.uuid4(),
                service_name=p["service_name"],
                service_type=p["service_type"],
                status=p["status"],
                latency_ms=p["latency_ms"],
                details=p.get("details", {}),
                checked_at=checked_at,
            )
            for p in pings
        ]
        return self._repo.bulk_create(entities)
