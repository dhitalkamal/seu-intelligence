"""DRF API views for intelligence endpoints."""
from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.health import check_database, check_rabbitmq, check_redis


class HealthCheckView(APIView):
    """Reports the operational status of all external dependencies."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        """Check DB, Redis, and RabbitMQ and return an aggregated status."""
        db_status, db_err = check_database()
        redis_status, redis_err = check_redis()
        rmq_status, rmq_err = check_rabbitmq()

        checks: dict = {
            "database": db_status,
            "redis": redis_status,
            "rabbitmq": rmq_status,
        }
        errors: dict = {
            k: v
            for k, v in {
                "database": db_err,
                "redis": redis_err,
                "rabbitmq": rmq_err,
            }.items()
            if v is not None
        }

        all_healthy = all(s == "healthy" for s in checks.values())

        if all_healthy:
            return Response(
                {
                    "data": {
                        "service": settings.SERVICE_NAME,
                        "status": "healthy",
                        "version": "0.1.0",
                        "checks": checks,
                    }
                },
                status=200,
            )

        return Response(
            {
                "type": "/errors/service-unavailable",
                "title": "Service Unhealthy",
                "status": 503,
                "detail": "One or more dependencies are unavailable.",
                "code": "SERVICE_UNHEALTHY",
                "checks": checks,
                **(({"errors": errors}) if errors else {}),
            },
            status=503,
            content_type="application/problem+json",
        )
