"""DRF API views for intelligence endpoints."""

from __future__ import annotations

import uuid

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.api.responses import created_response, error_response, success_response
from apps.common.health import check_database, check_rabbitmq, check_redis
from apps.intelligence.application.use_cases.calculate_health import CalculateHealthScoreUseCase
from apps.intelligence.application.use_cases.get_health import GetLatestHealthScoreUseCase
from apps.intelligence.application.use_cases.ingest_batch import IngestBatchUseCase
from apps.intelligence.application.use_cases.ingest_event import IngestEventUseCase
from apps.intelligence.infrastructure.repositories import (
    DjangoAnalyticsEventRepository,
    DjangoHealthScoreRepository,
)
from apps.intelligence.presentation.serializers import (
    HealthScoreInputSerializer,
    HealthScoreResponseSerializer,
    IngestEventSerializer,
)

_IS_AUTH = IsAuthenticated
_CREATED = created_response
_UUID = uuid.UUID
_INGEST_UC = IngestEventUseCase
_BATCH_UC = IngestBatchUseCase
_CALC_HEALTH_UC = CalculateHealthScoreUseCase
_GET_HEALTH_UC = GetLatestHealthScoreUseCase
_EVENT_REPO = DjangoAnalyticsEventRepository
_HEALTH_REPO = DjangoHealthScoreRepository
_INGEST_SER = IngestEventSerializer
_HEALTH_INPUT_SER = HealthScoreInputSerializer
_HEALTH_RESP_SER = HealthScoreResponseSerializer

_CHECKS = inline_serializer(
    name="DependencyChecks",
    fields={
        "database": serializers.ChoiceField(choices=["healthy", "unhealthy"]),
        "redis": serializers.ChoiceField(choices=["healthy", "unhealthy"]),
        "rabbitmq": serializers.ChoiceField(choices=["healthy", "unhealthy"]),
    },
)
_META_SCHEMA = inline_serializer(
    name="ResponseMeta",
    fields={
        "request_id": serializers.CharField(),
        "timestamp": serializers.CharField(),
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
                                "checks": _CHECKS,
                            },
                        ),
                        "error": serializers.JSONField(allow_null=True),
                        "meta": _META_SCHEMA,
                    },
                ),
            ),
            503: OpenApiResponse(
                description="One or more dependencies are unavailable.",
                response=inline_serializer(
                    name="UnhealthyResponse",
                    fields={
                        "data": serializers.JSONField(allow_null=True),
                        "error": inline_serializer(
                            name="HealthError",
                            fields={
                                "code": serializers.CharField(),
                                "message": serializers.CharField(),
                                "details": serializers.JSONField(allow_null=True),
                            },
                        ),
                        "meta": _META_SCHEMA,
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
            return success_response(
                {
                    "service": settings.SERVICE_NAME,
                    "status": "healthy",
                    "version": "0.1.0",
                    "checks": checks,
                },
                request=request,
            )

        return error_response(
            code="ERR_SERVICE_UNHEALTHY",
            message="One or more dependencies are unavailable.",
            details={"checks": checks, **({"errors": dep_errors} if dep_errors else {})},
            http_status=503,
            request=request,
        )


class IngestView(APIView):
    """Ingest a single analytics event or a batch depending on payload type."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Analytics"],
        summary="Ingest analytics event(s)",
        description=(
            "Submit a single event object to get back an id, "
            "or submit a JSON array to bulk-ingest and get back a count."
        ),
        request=_INGEST_SER,
        responses={
            201: OpenApiResponse(description="Event(s) ingested."),
            401: OpenApiResponse(description="Missing or invalid JWT."),
        },
    )
    def post(self, request: Request) -> Response:
        """Route to batch or single use case based on payload type."""
        if isinstance(request.data, list):
            ser = _INGEST_SER(data=request.data, many=True)
            ser.is_valid(raise_exception=True)
            count = _BATCH_UC(_EVENT_REPO()).execute(events=ser.validated_data)
            return _CREATED({"count": count}, request=request)

        ser = _INGEST_SER(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        record_id = _INGEST_UC(_EVENT_REPO()).execute(
            event_type=d["event_type"],
            source_service=d["source_service"],
            occurred_at=d["occurred_at"],
            event_id=d["event_id"],
            organisation_id=d["organisation_id"],
            user_id=d["user_id"],
            value=d["value"],
            payload=d["payload"],
        )
        return _CREATED({"id": record_id}, request=request)


class HealthScoreView(APIView):
    """Get or calculate the health score for an event."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Health Score"],
        summary="Get latest health score",
        responses={
            200: OpenApiResponse(description="Latest score found.", response=_HEALTH_RESP_SER),
            401: OpenApiResponse(description="Missing or invalid JWT."),
            404: OpenApiResponse(description="No score found for this event."),
        },
    )
    def get(self, request: Request, event_id: uuid.UUID) -> Response:
        """Return the most recently calculated health score for the event."""
        result = _GET_HEALTH_UC(_HEALTH_REPO()).execute(event_id=event_id)
        return success_response(_HEALTH_RESP_SER(result).data, request=request)

    @extend_schema(
        tags=["Health Score"],
        summary="Calculate health score",
        request=_HEALTH_INPUT_SER,
        responses={
            201: OpenApiResponse(description="Score calculated.", response=_HEALTH_RESP_SER),
            401: OpenApiResponse(description="Missing or invalid JWT."),
        },
    )
    def post(self, request: Request, event_id: uuid.UUID) -> Response:
        """Calculate and persist a new health score for the event."""
        ser = _HEALTH_INPUT_SER(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        result = _CALC_HEALTH_UC(_HEALTH_REPO()).execute(
            event_id=event_id,
            registration_velocity=d["registration_velocity"],
            conversion_rate=d["conversion_rate"],
            revenue_progress=d["revenue_progress"],
            capacity=d["capacity"],
            registered_count=d["registered_count"],
        )
        return _CREATED(_HEALTH_RESP_SER(result).data, request=request)


class NLPSearchView(APIView):
    """Tokenise a natural language query and return keywords."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["NLP"],
        summary="NLP search tokeniser",
        description="Splits the q param on whitespace and returns tokens longer than 2 characters.",
        responses={200: OpenApiResponse(description="Keywords extracted.")},
    )
    def get(self, request: Request) -> Response:
        """Return tokenised keywords from the q query parameter."""
        query = request.query_params.get("q", "")
        keywords = [t for t in query.split() if len(t) > 2]
        return success_response({"keywords": keywords, "filters": {}}, request=request)
