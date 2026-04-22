"""Unit tests for the real-time WebSocket dashboard broadcast utility."""

from __future__ import annotations


def test_format_health_event_contains_pings() -> None:
    """_format_health_event wraps pings under a 'data' key."""
    from apps.intelligence.presentation.consumers import _format_health_event

    pings = [{"service_name": "iam", "status": "healthy", "latency_ms": 30}]
    msg = _format_health_event(pings)

    assert msg["type"] == "health.update"
    assert msg["data"]["pings"] == pings


def test_format_health_event_empty_list() -> None:
    """_format_health_event handles an empty ping list gracefully."""
    from apps.intelligence.presentation.consumers import _format_health_event

    msg = _format_health_event([])
    assert msg["data"]["pings"] == []


def test_format_health_event_preserves_all_ping_fields() -> None:
    """All fields in each ping dict survive the formatting step unchanged."""
    from apps.intelligence.presentation.consumers import _format_health_event

    pings = [
        {"service_name": "redis", "service_type": "infrastructure", "status": "healthy", "latency_ms": 5, "details": {}},
        {"service_name": "minio", "service_type": "infrastructure", "status": "unreachable", "latency_ms": 5001, "details": {}},
    ]
    msg = _format_health_event(pings)

    assert msg["data"]["pings"][0]["service_type"] == "infrastructure"
    assert msg["data"]["pings"][1]["status"] == "unreachable"


def test_consumer_class_has_required_handlers() -> None:
    """HealthDashboardConsumer declares all required channel handlers."""
    from apps.intelligence.presentation.consumers import HealthDashboardConsumer

    assert hasattr(HealthDashboardConsumer, "connect")
    assert hasattr(HealthDashboardConsumer, "disconnect")
    assert hasattr(HealthDashboardConsumer, "health_update")


def test_consumer_group_name_is_stable() -> None:
    """group_name is a fixed string so all instances join the same broadcast group."""
    from apps.intelligence.presentation.consumers import HealthDashboardConsumer

    assert HealthDashboardConsumer.group_name == "health_dashboard"
