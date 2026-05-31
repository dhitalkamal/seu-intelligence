"""Shared fakes and fixtures for report generation unit tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from apps.intelligence.domain.entities import ReportJobEntity
from apps.intelligence.domain.exceptions import ReportJobNotFoundError
from apps.intelligence.domain.repositories import IReportJobRepository, IReportStorage


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_report_job(**kwargs: object) -> ReportJobEntity:
    """Build a ReportJobEntity with sensible defaults."""
    now = _now()
    defaults: dict = {
        "id": uuid.uuid4(),
        "requested_by": uuid.uuid4(),
        "report_type": "attendee_list",
        "filters": {},
        "format": "csv",
        "status": "pending",
        "file_url": None,
        "created_at": now,
        "completed_at": None,
    }
    defaults.update(kwargs)
    return ReportJobEntity(**defaults)  # type: ignore[arg-type]


class FakeReportJobRepository(IReportJobRepository):
    """In-memory report job store for testing."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, ReportJobEntity] = {}

    def create(self, entity: ReportJobEntity) -> ReportJobEntity:
        """Persist and return the entity."""
        self._store[entity.id] = entity
        return entity

    def get_by_id(self, job_id: uuid.UUID) -> ReportJobEntity:
        """Return the job or raise ReportJobNotFoundError."""
        entity = self._store.get(job_id)
        if entity is None:
            raise ReportJobNotFoundError("Report job not found.")
        return entity

    def update(self, entity: ReportJobEntity) -> ReportJobEntity:
        """Overwrite the stored entity."""
        self._store[entity.id] = entity
        return entity


class FakeReportStorage(IReportStorage):
    """In-memory storage fake that returns predictable presigned URLs."""

    def __init__(self) -> None:
        self.uploaded: list[tuple[str, bytes, str]] = []

    def upload(self, file_key: str, content: bytes, content_type: str) -> None:
        """Record the upload in memory."""
        self.uploaded.append((file_key, content, content_type))

    def generate_presigned_url(self, file_key: str, expires_in: int = 3600) -> str:
        """Return a deterministic fake URL for the given key."""
        return f"https://minio.fake/{file_key}?expires_in={expires_in}"


def noop_task(job_id: uuid.UUID) -> None:
    """Fake Celery task dispatcher, does nothing in unit tests."""
