"""Tests for GenerateReportUseCase."""

from __future__ import annotations

import uuid

from apps.intelligence.application.use_cases.generate_report import GenerateReportUseCase
from apps.intelligence.domain.entities import ReportJobEntity

from .conftest import FakeReportJobRepository, noop_task


class TestGenerateReport:
    """Unit tests for GenerateReportUseCase."""

    def test_creates_pending_job(self) -> None:
        """New job is persisted with status=pending."""
        repo = FakeReportJobRepository()
        sut = GenerateReportUseCase(repo, dispatch_task=noop_task)
        job = sut.execute(
            requested_by=uuid.uuid4(),
            report_type="attendee_list",
            filters={"event_id": str(uuid.uuid4())},
            format="csv",
        )
        assert job.status == "pending"

    def test_returns_report_job_entity(self) -> None:
        """execute returns a ReportJobEntity with the correct attributes."""
        repo = FakeReportJobRepository()
        sut = GenerateReportUseCase(repo, dispatch_task=noop_task)
        user_id = uuid.uuid4()
        job = sut.execute(
            requested_by=user_id,
            report_type="revenue",
            filters={},
            format="excel",
        )
        assert isinstance(job, ReportJobEntity)
        assert job.requested_by == user_id
        assert job.report_type == "revenue"
        assert job.format == "excel"
        assert job.file_url is None

    def test_dispatches_task(self) -> None:
        """The dispatch_task callable is called once with the new job id."""
        dispatched: list[uuid.UUID] = []

        def _capture_task(job_id: uuid.UUID) -> None:
            dispatched.append(job_id)

        repo = FakeReportJobRepository()
        sut = GenerateReportUseCase(repo, dispatch_task=_capture_task)
        job = sut.execute(requested_by=uuid.uuid4(), report_type="attendee_list", filters={}, format="csv")
        assert dispatched == [job.id]
