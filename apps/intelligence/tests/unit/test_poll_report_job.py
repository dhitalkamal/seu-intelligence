"""Tests for PollReportJobUseCase."""

from __future__ import annotations

import uuid

import pytest

from apps.intelligence.application.use_cases.poll_report_job import PollReportJobUseCase
from apps.intelligence.domain.exceptions import ReportJobNotFoundError

from .conftest import FakeReportJobRepository, make_report_job


class TestPollReportJob:
    """Unit tests for PollReportJobUseCase."""

    def test_returns_existing_job(self) -> None:
        """execute returns the job entity by id."""
        job = make_report_job()
        repo = FakeReportJobRepository()
        repo.create(job)
        result = PollReportJobUseCase(repo).execute(job_id=job.id)
        assert result.id == job.id
        assert result.status == "pending"

    def test_raises_if_not_found(self) -> None:
        """ReportJobNotFoundError raised for unknown job_id."""
        repo = FakeReportJobRepository()
        with pytest.raises(ReportJobNotFoundError):
            PollReportJobUseCase(repo).execute(job_id=uuid.uuid4())
