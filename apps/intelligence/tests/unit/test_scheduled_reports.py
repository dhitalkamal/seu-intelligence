"""Unit tests for scheduled report use cases."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest

from apps.intelligence.application.use_cases.create_scheduled_report import CreateScheduledReportUseCase
from apps.intelligence.application.use_cases.trigger_scheduled_reports import TriggerScheduledReportsUseCase
from apps.intelligence.domain.entities import ScheduledReportEntity
from apps.intelligence.domain.repositories import IScheduledReportRepository


class FakeScheduledReportRepository(IScheduledReportRepository):
    """In-memory store for scheduled report entities."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, ScheduledReportEntity] = {}

    def create(self, entity: ScheduledReportEntity) -> ScheduledReportEntity:
        """Persist entity and return it."""
        self._store[entity.id] = entity
        return entity

    def list_due(self, as_of: datetime) -> list[ScheduledReportEntity]:
        """Return active reports whose next_run_at is on or before as_of."""
        return [e for e in self._store.values() if e.is_active and e.next_run_at is not None and e.next_run_at <= as_of]

    def update(self, entity: ScheduledReportEntity) -> ScheduledReportEntity:
        """Overwrite the stored entity."""
        self._store[entity.id] = entity
        return entity

    def list_for_event(self, event_id: uuid.UUID) -> list[ScheduledReportEntity]:
        """Return all configs for the event."""
        return [e for e in self._store.values() if e.event_id == event_id]

    def deactivate(self, schedule_id: uuid.UUID) -> ScheduledReportEntity:
        """Mark the entity inactive."""
        entity = self._store[schedule_id]
        from dataclasses import replace as dc_replace

        updated = dc_replace(entity, is_active=False)
        self._store[schedule_id] = updated
        return updated


def test_create_scheduled_report_persists_entity() -> None:
    """CreateScheduledReportUseCase saves the entity with is_active=True."""
    repo = FakeScheduledReportRepository()
    uc = CreateScheduledReportUseCase(repo)

    result = uc.execute(
        event_id=uuid.uuid4(),
        requested_by=uuid.uuid4(),
        report_type="attendee_list",
        filters={},
        format="csv",
        cron_expression="0 9 * * 1",  # every Monday at 9am
    )

    assert result.is_active is True
    assert result.cron_expression == "0 9 * * 1"
    assert result.next_run_at is not None


def test_create_scheduled_report_invalid_cron_raises() -> None:
    """An invalid cron expression raises ValueError before persisting."""
    repo = FakeScheduledReportRepository()
    uc = CreateScheduledReportUseCase(repo)

    with pytest.raises(ValueError, match="cron"):
        uc.execute(
            event_id=uuid.uuid4(),
            requested_by=uuid.uuid4(),
            report_type="attendee_list",
            filters={},
            format="csv",
            cron_expression="not a cron",
        )

    assert len(repo._store) == 0


def test_trigger_scheduled_reports_dispatches_due_tasks() -> None:
    """TriggerScheduledReportsUseCase calls dispatch for each due report."""
    repo = FakeScheduledReportRepository()
    dispatched: list[Any] = []

    def fake_dispatch(job_id: uuid.UUID) -> None:
        dispatched.append(job_id)

    # seed a due report (next_run_at in the past)
    entity = ScheduledReportEntity(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        requested_by=uuid.uuid4(),
        report_type="attendee_list",
        filters={},
        format="csv",
        cron_expression="0 9 * * 1",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        next_run_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )
    repo.create(entity)

    from apps.intelligence.domain.entities import ReportJobEntity
    from apps.intelligence.domain.repositories import IReportJobRepository

    class FakeJobRepo(IReportJobRepository):
        def create(self, e: ReportJobEntity) -> ReportJobEntity:
            return e

        def get_by_id(self, job_id: uuid.UUID) -> ReportJobEntity:  # pragma: no cover
            raise NotImplementedError

        def update(self, e: ReportJobEntity) -> ReportJobEntity:  # pragma: no cover
            raise NotImplementedError

    uc = TriggerScheduledReportsUseCase(repo, FakeJobRepo(), dispatch_task=fake_dispatch)
    count = uc.execute()

    assert count == 1
    assert len(dispatched) == 1


def test_trigger_scheduled_reports_updates_next_run_at() -> None:
    """After triggering, next_run_at is advanced to the next cron occurrence."""
    repo = FakeScheduledReportRepository()
    dispatched: list[Any] = []

    entity = ScheduledReportEntity(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        requested_by=uuid.uuid4(),
        report_type="attendee_list",
        filters={},
        format="csv",
        cron_expression="0 9 * * 1",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        next_run_at=datetime(2020, 1, 6, 9, 0, tzinfo=timezone.utc),  # a Monday
    )
    repo.create(entity)

    from apps.intelligence.domain.entities import ReportJobEntity
    from apps.intelligence.domain.repositories import IReportJobRepository

    class FakeJobRepo(IReportJobRepository):
        def create(self, e: ReportJobEntity) -> ReportJobEntity:
            return e

        def get_by_id(self, job_id: uuid.UUID) -> ReportJobEntity:  # pragma: no cover
            raise NotImplementedError

        def update(self, e: ReportJobEntity) -> ReportJobEntity:  # pragma: no cover
            raise NotImplementedError

    uc = TriggerScheduledReportsUseCase(repo, FakeJobRepo(), dispatch_task=lambda _: dispatched.append(True))
    uc.execute()

    updated = repo._store[entity.id]
    # next_run_at should have advanced past the original 2020-01-06
    assert updated.next_run_at > entity.next_run_at
