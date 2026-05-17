"""Use case: ingest a single analytics event."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from apps.intelligence.domain.entities import AnalyticsEventEntity
from apps.intelligence.domain.repositories import IAnalyticsEventRepository


class IngestEventUseCase:
    """Persist a single analytics event and return its id."""

    def __init__(self, repo: IAnalyticsEventRepository) -> None:
        self._repo = repo

    def execute(
        self,
        *,
        event_type: str,
        source_service: str,
        occurred_at: datetime,
        event_id: uuid.UUID | None = None,
        organisation_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        value: Decimal | None = None,
        payload: dict | None = None,
    ) -> str:
        """Build and persist an analytics event. Returns the string UUID of the record."""
        entity = AnalyticsEventEntity(
            id=uuid.uuid4(),
            event_type=event_type,
            source_service=source_service,
            occurred_at=occurred_at,
            created_at=datetime.now(timezone.utc),
            event_id=event_id,
            organisation_id=organisation_id,
            user_id=user_id,
            value=value,
            payload=payload or {},
        )
        saved = self._repo.create(entity)
        return str(saved.id)
