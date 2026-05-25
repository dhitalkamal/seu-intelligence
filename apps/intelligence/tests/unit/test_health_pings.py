"""Unit tests for health ping use cases."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from apps.intelligence.application.use_cases.cleanup_health_pings import CleanupHealthPingsUseCase
from apps.intelligence.application.use_cases.get_health_history import GetHealthHistoryUseCase, GetLatestHealthRoundUseCase
from apps.intelligence.application.use_cases.record_health_pings import RecordHealthPingsUseCase
from apps.intelligence.tests.unit.fakes import FakeHealthPingRepository, make_ping


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestRecordHealthPings:
    def test_stores_pings_and_returns_count(self) -> None:
        repo = FakeHealthPingRepository()
        pings = [
            {"service_name": "iam", "service_type": "application", "status": "healthy", "latency_ms": 20, "details": {}},
            {"service_name": "redis", "service_type": "infrastructure", "status": "healthy", "latency_ms": 5, "details": {}},
        ]
        count = RecordHealthPingsUseCase(repo).execute(pings=pings, checked_at=_now())
        assert count == 2
        assert len(repo._store) == 2

    def test_stores_correct_service_names(self) -> None:
        repo = FakeHealthPingRepository()
        pings = [
            {"service_name": "elasticsearch", "service_type": "infrastructure", "status": "healthy", "latency_ms": 30},
        ]
        RecordHealthPingsUseCase(repo).execute(pings=pings, checked_at=_now())
        assert repo._store[0].service_name == "elasticsearch"


class TestGetHealthHistory:
    def test_returns_all_when_no_filters(self) -> None:
        repo = FakeHealthPingRepository()
        repo._store = [make_ping(service_name="iam"), make_ping(service_name="redis")]
        result = GetHealthHistoryUseCase(repo).execute()
        assert len(result) == 2

    def test_filters_by_service_name(self) -> None:
        repo = FakeHealthPingRepository()
        repo._store = [make_ping(service_name="iam"), make_ping(service_name="redis")]
        result = GetHealthHistoryUseCase(repo).execute(service_name="redis")
        assert len(result) == 1
        assert result[0].service_name == "redis"

    def test_filters_by_since(self) -> None:
        repo = FakeHealthPingRepository()
        old = _now() - timedelta(days=40)
        recent = _now() - timedelta(hours=1)
        repo._store = [make_ping(checked_at=old), make_ping(checked_at=recent)]
        since = _now() - timedelta(days=30)
        result = GetHealthHistoryUseCase(repo).execute(since=since)
        assert len(result) == 1


class TestGetLatestHealthRound:
    def test_returns_latest_round(self) -> None:
        repo = FakeHealthPingRepository()
        t1 = _now() - timedelta(minutes=10)
        t2 = _now()
        repo._store = [
            make_ping(service_name="iam", checked_at=t1),
            make_ping(service_name="redis", checked_at=t1),
            make_ping(service_name="iam", checked_at=t2),
            make_ping(service_name="redis", checked_at=t2),
        ]
        result = GetLatestHealthRoundUseCase(repo).execute()
        assert len(result) == 2
        assert all(p.checked_at == t2 for p in result)

    def test_returns_empty_when_no_data(self) -> None:
        repo = FakeHealthPingRepository()
        result = GetLatestHealthRoundUseCase(repo).execute()
        assert result == []


class TestCleanupHealthPings:
    def test_deletes_old_pings(self) -> None:
        repo = FakeHealthPingRepository()
        old = _now() - timedelta(days=40)
        recent = _now()
        repo._store = [make_ping(checked_at=old), make_ping(checked_at=recent)]
        deleted = CleanupHealthPingsUseCase(repo).execute()
        assert deleted == 1
        assert len(repo._store) == 1
        assert repo._store[0].checked_at == recent

    def test_no_op_when_all_recent(self) -> None:
        repo = FakeHealthPingRepository()
        repo._store = [make_ping(checked_at=_now()), make_ping(checked_at=_now())]
        deleted = CleanupHealthPingsUseCase(repo).execute()
        assert deleted == 0
        assert len(repo._store) == 2
