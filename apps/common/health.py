"""Dependency health checks for PostgreSQL, Redis, and RabbitMQ."""
from __future__ import annotations

import pika
import redis as redis_lib
from django.conf import settings
from django.db import connection


def check_database() -> tuple[str, str | None]:
    """Run SELECT 1 against the default DB. Returns (status, error_msg)."""
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return "healthy", None
    except Exception as exc:
        return "unhealthy", str(exc)


def check_redis() -> tuple[str, str | None]:
    """Ping Redis with a 2-second connect timeout. Returns (status, error_msg)."""
    try:
        client = redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        client.ping()
        return "healthy", None
    except Exception as exc:
        return "unhealthy", str(exc)


def check_rabbitmq() -> tuple[str, str | None]:
    """Open and close a RabbitMQ connection with a 2-second socket timeout."""
    try:
        params = pika.URLParameters(settings.RABBITMQ_URL)
        params.socket_timeout = 2
        conn = pika.BlockingConnection(params)
        conn.close()
        return "healthy", None
    except Exception as exc:
        return "unhealthy", str(exc)
