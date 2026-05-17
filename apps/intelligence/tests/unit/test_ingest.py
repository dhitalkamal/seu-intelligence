"""Unit tests for IngestEventUseCase and IngestBatchUseCase."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from apps.intelligence.application.use_cases.ingest_batch import IngestBatchUseCase
from apps.intelligence.application.use_cases.ingest_event import IngestEventUseCase
from apps.intelligence.tests.unit.fakes import FakeAnalyticsEventRepository


def _now() -> datetime:
    return datetime.now(timezone.utc)


def test_ingest_single_returns_string_uuid():
    """Single ingest returns a valid UUID string."""
    repo = FakeAnalyticsEventRepository()
    result = IngestEventUseCase(repo).execute(
        event_type="registration.created",
        source_service="participation-service",
        occurred_at=_now(),
    )
    assert isinstance(result, str)
    uuid.UUID(result)


def test_ingest_batch_returns_count():
    """Batch ingest returns the number of persisted records."""
    repo = FakeAnalyticsEventRepository()
    events = [
        {
            "event_type": "registration.created",
            "source_service": "participation-service",
            "occurred_at": _now(),
        },
        {
            "event_type": "payment.completed",
            "source_service": "payment-service",
            "occurred_at": _now(),
        },
    ]
    count = IngestBatchUseCase(repo).execute(events=events)
    assert count == 2


def test_ingest_batch_empty_returns_zero():
    """Batch ingest with an empty list persists nothing and returns 0."""
    repo = FakeAnalyticsEventRepository()
    count = IngestBatchUseCase(repo).execute(events=[])
    assert count == 0
