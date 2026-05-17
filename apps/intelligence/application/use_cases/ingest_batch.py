"""Use case: ingest a batch of analytics events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from apps.intelligence.domain.entities import AnalyticsEventEntity
from apps.intelligence.domain.repositories import IAnalyticsEventRepository


class IngestBatchUseCase:
    """Persist multiple analytics events and return the count."""

    def __init__(self, repo: IAnalyticsEventRepository) -> None:
        self._repo = repo

    def execute(self, *, events: list[dict]) -> int:
        """
        Build and bulk-insert all provided events.

        @param events - list of dicts each matching IngestEventUseCase params
        @returns count of inserted records
        """
        if not events:
            return 0

        now = datetime.now(timezone.utc)
        entities = [
            AnalyticsEventEntity(
                id=uuid.uuid4(),
                event_type=e["event_type"],
                source_service=e["source_service"],
                occurred_at=e["occurred_at"],
                created_at=now,
                event_id=e.get("event_id"),
                organisation_id=e.get("organisation_id"),
                user_id=e.get("user_id"),
                value=e.get("value"),
                payload=e.get("payload", {}),
            )
            for e in events
        ]
        return self._repo.bulk_create(entities)
