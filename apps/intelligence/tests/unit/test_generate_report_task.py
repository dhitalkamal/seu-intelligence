"""Tests for generate_report_task Celery task."""

from __future__ import annotations

import uuid

from apps.intelligence.tests.unit.conftest import FakeReportJobRepository, FakeReportStorage, make_report_job


class TestGenerateReportTask:
    """Unit tests for generate_report_task."""

    def _run_task(self, job_id: uuid.UUID, repo: FakeReportJobRepository) -> FakeReportStorage:
        """Import and call the task function directly (no Celery broker)."""
        from apps.intelligence.tasks import _run_generate_report

        storage = FakeReportStorage()
        _run_generate_report(job_id=job_id, repo=repo, storage=storage)
        return storage

    def test_sets_status_completed(self) -> None:
        """Task marks job as completed after generating the file."""
        job = make_report_job(status="pending", report_type="attendee_list", format="csv")
        repo = FakeReportJobRepository()
        repo.create(job)
        self._run_task(job.id, repo)
        updated = repo.get_by_id(job.id)
        assert updated.status == "completed"

    def test_sets_file_url(self) -> None:
        """Task sets file_url to a non-empty string after upload."""
        job = make_report_job(status="pending", report_type="attendee_list", format="csv")
        repo = FakeReportJobRepository()
        repo.create(job)
        self._run_task(job.id, repo)
        updated = repo.get_by_id(job.id)
        assert updated.file_url is not None
        assert len(updated.file_url) > 0

    def test_sets_completed_at(self) -> None:
        """Task sets completed_at timestamp."""
        job = make_report_job(status="pending", report_type="attendee_list", format="csv")
        repo = FakeReportJobRepository()
        repo.create(job)
        self._run_task(job.id, repo)
        updated = repo.get_by_id(job.id)
        assert updated.completed_at is not None
