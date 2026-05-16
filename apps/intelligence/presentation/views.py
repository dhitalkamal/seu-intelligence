"""DRF API views for intelligence endpoints."""
from __future__ import annotations

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.health import check_database, check_rabbitmq, check_redis

# Reusable check-status schema shared by the healthy and unhealthy responses.
_DEPENDENCY_CHECKS = inline_serializer(
    name="DependencyChecks",
    fields={
        "database": serializers.ChoiceField(choices=["healthy", "unhealthy"]),
        "redis": serializers.ChoiceField(choices=["healthy", "unhealthy"]),
        "rabbitmq": serializers.ChoiceField(choices=["healthy", "unhealthy"]),
    },
)


class HealthCheckView(APIView):
    """Reports the operational status of all external dependencies."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Health"],
        summary="Service health check",
        description=(
            "Checks connectivity to PostgreSQL, Redis, and RabbitMQ. "
            "Returns 200 when all dependencies are healthy, 503 when any are down."
        ),
        auth=[],
        responses={
            200: OpenApiResponse(
                description="All dependencies are healthy.",
                response=inline_serializer(
                    name="HealthyResponse",
                    fields={
                        "data": inline_serializer(
                            name="HealthyData",
                            fields={
                                "service": serializers.CharField(),
                                "status": serializers.CharField(),
                                "version": serializers.CharField(),
                                "checks": _DEPENDENCY_CHECKS,
                            },
                        ),
                    },
                ),
            ),
            503: OpenApiResponse(
                description="One or more dependencies are unavailable.",
                response=inline_serializer(
                    name="UnhealthyResponse",
                    fields={
                        "type": serializers.CharField(),
                        "title": serializers.CharField(),
                        "status": serializers.IntegerField(),
                        "detail": serializers.CharField(),
                        "code": serializers.CharField(),
                        "checks": _DEPENDENCY_CHECKS,
                    },
                ),
            ),
        },
    )
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
        dep_errors: dict = {
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
                **({"errors": dep_errors} if dep_errors else {}),
            },
            status=503,
            content_type="application/problem+json",
        )
