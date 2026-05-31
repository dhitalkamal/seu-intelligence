"""Use case: delete health ping records older than retention window."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from apps.intelligence.domain.repositories import IHealthPingRepository

RETENTION_DAYS = 31


class CleanupHealthPingsUseCase:
    """Remove stale health ping rows beyond the retention window."""

    def __init__(self, repo: IHealthPingRepository) -> None:
        self._repo = repo

    def execute(self) -> int:
        """Delete rows older than 31 days and return count deleted."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        return self._repo.delete_older_than(cutoff)
