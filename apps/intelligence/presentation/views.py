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
from apps.intelligence.application.use_cases.get_connections import GetConnectionsUseCase
from apps.intelligence.application.use_cases.get_health import GetLatestHealthScoreUseCase
from apps.intelligence.application.use_cases.get_privacy import GetPrivacyUseCase
from apps.intelligence.application.use_cases.ingest_batch import IngestBatchUseCase
from apps.intelligence.application.use_cases.ingest_event import IngestEventUseCase
from apps.intelligence.application.use_cases.send_introduction import SendIntroductionUseCase
from apps.intelligence.application.use_cases.tokenize import tokenize_query
from apps.intelligence.application.use_cases.update_privacy import UpdatePrivacyUseCase
from apps.intelligence.domain.exceptions import MatchNotFoundError, OptInRequiredError
from apps.intelligence.infrastructure.repositories import (
    DjangoAnalyticsEventQueryRepository,
    DjangoAnalyticsEventRepository,
    DjangoAttendeeMatchRepository,
    DjangoConnectionPrivacyRepository,
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
_GET_CONNECTIONS_UC = GetConnectionsUseCase
_SEND_INTRO_UC = SendIntroductionUseCase
_GET_PRIVACY_UC = GetPrivacyUseCase
_UPDATE_PRIVACY_UC = UpdatePrivacyUseCase
_EVENT_REPO = DjangoAnalyticsEventRepository
_HEALTH_REPO = DjangoHealthScoreRepository
_MATCH_REPO = DjangoAttendeeMatchRepository
_PRIVACY_REPO = DjangoConnectionPrivacyRepository
_ANALYTICS_QUERY_REPO = DjangoAnalyticsEventQueryRepository
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
    """Tokenise a natural language query in English or Nepali."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["NLP"],
        summary="NLP search tokeniser (English + Nepali)",
        description=(
            "Detects the query language from script (Devanagari = Nepali, Latin = English), "
            "then tokenises and filters stop words. Returns keywords, detected language, "
            "and a filters dict for future structured extraction."
        ),
        responses={200: OpenApiResponse(description="Keywords extracted.")},
    )
    def get(self, request: Request) -> Response:
        """Tokenise the q query parameter using the appropriate language handler."""
        query = request.query_params.get("q", "")
        result = tokenize_query(query)
        return success_response(result, request=request)


class ConnectionsView(APIView):
    """GET /events/{event_id}/connections/ - Who to Meet suggestions."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Who to Meet"],
        summary="Get Who to Meet suggestions",
        description=(
            "Returns ranked attendee suggestions for the authenticated user at this event. "
            "The user must have opted in via PATCH /events/{event_id}/connections/settings/. "
            "Scores are computed using Jaccard similarity on past event attendance."
        ),
        responses={
            200: OpenApiResponse(description="Match suggestions returned."),
            403: OpenApiResponse(description="User has not opted in."),
        },
    )
    def get(self, request: Request, event_id: uuid.UUID) -> Response:
        """Return ranked Who to Meet suggestions for the authenticated user."""
        try:
            matches = _GET_CONNECTIONS_UC(
                _MATCH_REPO(), _PRIVACY_REPO(), _ANALYTICS_QUERY_REPO()
            ).execute(event_id=event_id, requesting_user_id=uuid.UUID(str(request.user.id)))
        except OptInRequiredError as exc:
            return error_response(code=exc.code, message=str(exc), http_status=403, request=request)
        data = [
            {
                "match_id": str(m.id),
                "user_id": str(
                    m.user_id_b if m.user_id_a == uuid.UUID(str(request.user.id)) else m.user_id_a
                ),
                "match_score": str(m.match_score),
                "match_signals": m.match_signals,
                "is_introduced": m.is_introduced,
                "introduced_at": m.introduced_at.isoformat() if m.introduced_at else None,
            }
            for m in matches
        ]
        return success_response(data, request=request)


class IntroductionView(APIView):
    """POST /events/{event_id}/connections/{user_id}/introduce/ - send introduction."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Who to Meet"],
        summary="Send introduction request",
        description="Marks both attendees as introduced. Both must have opted in.",
        responses={
            200: OpenApiResponse(description="Introduction sent."),
            403: OpenApiResponse(description="Target user has not opted in."),
            404: OpenApiResponse(description="No match record found."),
        },
    )
    def post(self, request: Request, event_id: uuid.UUID, user_id: uuid.UUID) -> Response:
        """Mark the two users as introduced."""
        try:
            match = _SEND_INTRO_UC(_MATCH_REPO(), _PRIVACY_REPO()).execute(
                event_id=event_id,
                requesting_user_id=uuid.UUID(str(request.user.id)),
                target_user_id=user_id,
            )
        except OptInRequiredError as exc:
            return error_response(code=exc.code, message=str(exc), http_status=403, request=request)
        except MatchNotFoundError as exc:
            return error_response(code=exc.code, message=str(exc), http_status=404, request=request)
        return success_response(
            {"match_id": str(match.id), "is_introduced": match.is_introduced},
            request=request,
        )


class ConnectionPrivacyView(APIView):
    """GET/PATCH /events/{event_id}/connections/settings/ - privacy opt-in."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Who to Meet"],
        summary="Get privacy settings",
        responses={200: OpenApiResponse(description="Privacy settings returned.")},
    )
    def get(self, request: Request, event_id: uuid.UUID) -> Response:
        """Return the current opt-in preference for this user and event."""
        pref = _GET_PRIVACY_UC(_PRIVACY_REPO()).execute(
            user_id=uuid.UUID(str(request.user.id)), event_id=event_id
        )
        return success_response(
            {"opted_in": pref.opted_in, "event_id": str(event_id)}, request=request
        )

    @extend_schema(
        tags=["Who to Meet"],
        summary="Update privacy settings",
        responses={200: OpenApiResponse(description="Settings updated.")},
    )
    def patch(self, request: Request, event_id: uuid.UUID) -> Response:
        """Opt in or out of the Who to Meet feature for this event."""
        opted_in = request.data.get("opted_in")
        if opted_in is None or not isinstance(opted_in, bool):
            return error_response(
                code="ERR_CONNECTIONS_INVALID_PAYLOAD",
                message="opted_in (boolean) is required.",
                http_status=400,
                request=request,
            )
        pref = _UPDATE_PRIVACY_UC(_PRIVACY_REPO()).execute(
            user_id=uuid.UUID(str(request.user.id)),
            event_id=event_id,
            opted_in=opted_in,
        )
        return success_response({"opted_in": pref.opted_in}, request=request)
