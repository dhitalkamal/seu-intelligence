"""Celery tasks for the intelligence service."""

from __future__ import annotations

import time
from datetime import datetime, timezone

import requests
from celery import shared_task

# backend services: name -> internal docker url
APPLICATION_SERVICES = {
    "iam": "http://iam:8001/api/v1/health/",
    "event": "http://event:8002/api/v1/health/",
    "participation": "http://participation:8003/api/v1/health/",
    "payment": "http://payment:8004/api/v1/health/",
    "notification": "http://notification:8005/api/v1/health/",
    "management": "http://management:8006/api/v1/health/",
    "intelligence": "http://intelligence:8007/api/v1/health/",
}

# infra services: name -> (url, parser)
INFRA_SERVICES = {
    "elasticsearch": "http://elasticsearch:9200/_cluster/health",
    "rabbitmq": "http://rabbitmq:15672/api/health/checks/alarms",
    "minio": "http://minio:9000/minio/health/live",
}

RABBITMQ_AUTH = ("sansaar", "sansaar_secret")
TIMEOUT_S = 5


def _ping_url(url: str, auth: tuple[str, str] | None = None) -> dict:
    """Hit a url and return status + latency."""
    t0 = time.monotonic()
    try:
        r = requests.get(url, timeout=TIMEOUT_S, auth=auth)
        latency = int((time.monotonic() - t0) * 1000)
        return {
            "latency_ms": latency,
            "status_code": r.status_code,
            "body": r.json() if r.headers.get("content-type", "").startswith("application/json") else {},
        }
    except Exception:
        latency = int((time.monotonic() - t0) * 1000)
        return {"latency_ms": latency, "status_code": 0, "body": {}}


def _check_redis() -> dict:
    """Ping redis directly via the redis client."""
    t0 = time.monotonic()
    try:
        import redis as redis_lib
        from django.conf import settings

        client = redis_lib.from_url(settings.REDIS_URL)
        client.ping()
        latency = int((time.monotonic() - t0) * 1000)
        return {"status": "healthy", "latency_ms": latency, "details": {}}
    except Exception:
        latency = int((time.monotonic() - t0) * 1000)
        return {"status": "unreachable", "latency_ms": latency, "details": {}}


@shared_task(name="intelligence.ping_all_services")
def ping_all_services() -> dict:
    """Ping every service and infra dependency, store results."""
    from apps.intelligence.application.use_cases.cleanup_health_pings import CleanupHealthPingsUseCase
    from apps.intelligence.application.use_cases.record_health_pings import RecordHealthPingsUseCase
    from apps.intelligence.infrastructure.repositories import DjangoHealthPingRepository

    now = datetime.now(timezone.utc)
    pings: list[dict] = []

    # application services
    for name, url in APPLICATION_SERVICES.items():
        result = _ping_url(url)
        body = result["body"]
        data = body.get("data", body) if isinstance(body, dict) else {}
        status = "healthy" if result["status_code"] == 200 and data.get("status") == "healthy" else "unhealthy"
        if result["status_code"] == 0:
            status = "unreachable"
        pings.append(
            {
                "service_name": name,
                "service_type": "application",
                "status": status,
                "latency_ms": result["latency_ms"],
                "details": data.get("checks", {}),
            }
        )

    # redis
    redis_result = _check_redis()
    pings.append(
        {
            "service_name": "redis",
            "service_type": "infrastructure",
            "status": redis_result["status"],
            "latency_ms": redis_result["latency_ms"],
            "details": {},
        }
    )

    # rabbitmq
    rmq = _ping_url(INFRA_SERVICES["rabbitmq"], auth=RABBITMQ_AUTH)
    rmq_status = "healthy" if rmq["status_code"] == 200 and rmq["body"].get("status") == "ok" else "unreachable"
    pings.append(
        {
            "service_name": "rabbitmq",
            "service_type": "infrastructure",
            "status": rmq_status,
            "latency_ms": rmq["latency_ms"],
            "details": rmq["body"] if isinstance(rmq["body"], dict) else {},
        }
    )

    # elasticsearch
    es = _ping_url(INFRA_SERVICES["elasticsearch"])
    es_body = es["body"] if isinstance(es["body"], dict) else {}
    es_cluster = es_body.get("status", "")
    es_status = "healthy" if es["status_code"] == 200 and es_cluster in ("green", "yellow") else "unreachable"
    pings.append(
        {
            "service_name": "elasticsearch",
            "service_type": "infrastructure",
            "status": es_status,
            "latency_ms": es["latency_ms"],
            "details": {"cluster": es_cluster, "nodes": es_body.get("number_of_nodes", 0), "shards": es_body.get("active_shards", 0)},
        }
    )

    # minio
    minio = _ping_url(INFRA_SERVICES["minio"])
    minio_status = "healthy" if minio["status_code"] == 200 else "unreachable"
    pings.append(
        {
            "service_name": "minio",
            "service_type": "infrastructure",
            "status": minio_status,
            "latency_ms": minio["latency_ms"],
            "details": {},
        }
    )

    repo = DjangoHealthPingRepository()
    count = RecordHealthPingsUseCase(repo).execute(pings=pings, checked_at=now)

    # cleanup old rows once per run
    deleted = CleanupHealthPingsUseCase(repo).execute()

    return {"stored": count, "cleaned": deleted}
