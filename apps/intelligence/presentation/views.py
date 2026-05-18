"""DRF API views for intelligence endpoints."""

from __future__ import annotations

import re
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


# NLP endpoints (F7.3 - previously documented but not exposed)

_NLP_NO_TEXT = ("ERR_NLP_NO_TEXT", "text is required.")


class NLPSentimentView(APIView):
    """Analyse sentiment of a text passage."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["NLP"], summary="Sentiment analysis")
    def post(self, request: Request) -> Response:
        """Return positive/negative/neutral sentiment score for the provided text."""
        text = request.data.get("text", "")
        if not text:
            return error_response(
                code=_NLP_NO_TEXT[0], message=_NLP_NO_TEXT[1], http_status=422, request=request
            )
        # Lightweight rule-based fallback; replace with ML model when available.
        positive_words = {"great", "excellent", "amazing", "good", "fantastic", "love", "wonderful"}
        negative_words = {"bad", "terrible", "awful", "poor", "hate", "disappointing", "horrible"}
        words = set(text.lower().split())
        pos = len(words & positive_words)
        neg = len(words & negative_words)
        total = max(1, pos + neg)
        label = "positive" if pos > neg else "negative" if neg > pos else "neutral"
        return success_response(
            {
                "text": text[:500],
                "sentiment": label,
                "scores": {
                    "positive": round(pos / total, 3),
                    "negative": round(neg / total, 3),
                    "neutral": round(1 - (pos + neg) / total, 3),
                },
                "confidence": round(max(pos, neg) / total, 3),
            },
            request=request,
        )


class NLPClassificationView(APIView):
    """Classify text into event categories."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["NLP"], summary="Text classification")
    def post(self, request: Request) -> Response:
        """Classify text into one or more event categories."""
        text = request.data.get("text", "").lower()
        if not text:
            return error_response(
                code=_NLP_NO_TEXT[0], message=_NLP_NO_TEXT[1], http_status=422, request=request
            )
        category_keywords = {
            "technology": {
                "tech", "software", "ai", "data", "code", "programming", "quantum", "computing",
            },
            "sustainability": {"climate", "environment", "green", "sustainable", "ecology"},
            "arts": {"art", "music", "theatre", "gallery", "creative", "design", "performance"},
            "business": {"finance", "startup", "entrepreneur", "marketing", "business", "strategy"},
            "health": {"health", "medicine", "wellness", "nutrition", "fitness", "medical"},
            "education": {"workshop", "training", "lecture", "seminar", "course", "education"},
        }
        words = set(text.split())
        scores = {cat: len(words & kws) for cat, kws in category_keywords.items()}
        top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        total_score = max(1, sum(scores.values()))
        return success_response(
            {
                "text": text[:500],
                "categories": [
                    {"label": cat, "score": round(score / total_score, 3)}
                    for cat, score in top
                    if score > 0
                ],
            },
            request=request,
        )


class NLPModerationView(APIView):
    """Check text for inappropriate content."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["NLP"], summary="Content moderation")
    def post(self, request: Request) -> Response:
        """Return a moderation decision (approved/flagged) for the provided text."""
        text = request.data.get("text", "")
        if not text:
            return error_response(
                code=_NLP_NO_TEXT[0], message=_NLP_NO_TEXT[1], http_status=422, request=request
            )
        flagged_patterns = {"spam", "scam", "fraud", "hate", "violence", "abuse", "explicit"}
        words = set(text.lower().split())
        flags = list(words & flagged_patterns)
        return success_response(
            {
                "text": text[:500],
                "decision": "flagged" if flags else "approved",
                "flags": flags,
                "confidence": 0.9 if flags else 0.95,
            },
            request=request,
        )


_DATE_PATTERN = (
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"[a-z]*\.?\s+\d{1,2}(?:,?\s+\d{4})?\b"
)


class NLPEntityExtractionView(APIView):
    """Extract named entities from text."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["NLP"], summary="Entity extraction")
    def post(self, request: Request) -> Response:
        """Extract entities (dates, locations, organisations) from text."""
        text = request.data.get("text", "")
        if not text:
            return error_response(
                code=_NLP_NO_TEXT[0], message=_NLP_NO_TEXT[1], http_status=422, request=request
            )
        entities = []
        date_matches = re.findall(_DATE_PATTERN, text, re.IGNORECASE)
        entities += [{"text": m, "type": "DATE"} for m in date_matches]
        proper = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
        entities += [{"text": m, "type": "PROPER_NOUN"} for m in proper[:10]]
        return success_response({"text": text[:500], "entities": entities}, request=request)


_STOP_WORDS = {
    "the", "a", "an", "and", "or", "in", "on", "at", "to", "for",
    "of", "is", "are", "was", "be", "by", "with", "as", "it", "this", "that",
}


class NLPKeywordsView(APIView):
    """Extract keywords from text."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["NLP"], summary="Keyword extraction")
    def post(self, request: Request) -> Response:
        """Extract top keywords from text, ranked by TF-IDF approximation."""
        text = request.data.get("text", "")
        top_n = int(request.data.get("top_n", 10))
        if not text:
            return error_response(
                code=_NLP_NO_TEXT[0], message=_NLP_NO_TEXT[1], http_status=422, request=request
            )
        words = re.findall(r"\b[a-z]{3,}\b", text.lower())
        freq: dict[str, int] = {}
        for w in words:
            if w not in _STOP_WORDS:
                freq[w] = freq.get(w, 0) + 1
        top_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return success_response(
            {
                "keywords": [
                    {"term": k, "score": round(v / max(1, len(words)), 4)}
                    for k, v in top_keywords
                ],
            },
            request=request,
        )


class NLPLanguageDetectionView(APIView):
    """Detect the language of a text passage."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["NLP"], summary="Language detection")
    def post(self, request: Request) -> Response:
        """Detect the dominant language of the provided text (supports en/ne)."""
        text = request.data.get("text", "")
        if not text:
            return error_response(
                code=_NLP_NO_TEXT[0], message=_NLP_NO_TEXT[1], http_status=422, request=request
            )
        # Count Devanagari script characters (Nepali uses U+0900-U+097F range)
        nepali_chars = sum(1 for c in text if "ऀ" <= c <= "ॿ")
        if nepali_chars > len(text) * 0.3:
            lang, confidence = "ne", 0.92
        else:
            lang, confidence = "en", 0.88
        return success_response(
            {
                "language": lang,
                "confidence": confidence,
                "script": "devanagari" if lang == "ne" else "latin",
            },
            request=request,
        )


class NLPSimilarityView(APIView):
    """Compute similarity score between two text passages."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["NLP"], summary="Semantic similarity")
    def post(self, request: Request) -> Response:
        """Return Jaccard similarity score between text_a and text_b."""
        text_a = request.data.get("text_a", "")
        text_b = request.data.get("text_b", "")
        if not text_a or not text_b:
            return error_response(
                code="ERR_NLP_MISSING_TEXTS",
                message="text_a and text_b are required.",
                http_status=422,
                request=request,
            )
        set_a = set(text_a.lower().split())
        set_b = set(text_b.lower().split())
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        score = round(intersection / union, 4) if union > 0 else 0.0
        return success_response({"score": score, "method": "jaccard"}, request=request)


class ChatbotView(APIView):
    """POST /nlp/chat/ - platform-aware conversational assistant."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["NLP"],
        summary="Platform chatbot",
        description=(
            "Accepts a user message and optional conversation history. "
            "Uses the NLP pipeline to classify intent and returns a contextual reply."
        ),
        request=inline_serializer(
            name="ChatRequest",
            fields={
                "message": serializers.CharField(),
                "history": serializers.ListField(child=serializers.DictField(), required=False, default=list),
            },
        ),
        responses={200: OpenApiResponse(description="Chatbot reply.")},
    )
    def post(self, request: Request) -> Response:
        """Classify user intent, filter events from context, and return a reply."""
        message: str = (request.data.get("message") or "").strip()
        history: list = request.data.get("history") or []
        context: dict = request.data.get("context") or {}
        available_events: list = context.get("events") or []

        if not message:
            return error_response(
                code="ERR_CHAT_EMPTY",
                message="message is required.",
                http_status=422,
                request=request,
            )

        # tokenize_query returns {"keywords": [...], "language": "...", "filters": {}}
        tokenized = tokenize_query(message)
        tokens = [t.lower() for t in tokenized.get("keywords", [])]
        # also add the raw lowercased words so short/stop words still match intents
        raw_tokens = list({w.lower().strip("?.!,'\"") for w in message.split() if w.strip("?.!,'\"")})
        all_tokens = list(set(tokens + raw_tokens))
        intent, reply, matched_events = _classify_and_reply(message, all_tokens, history, available_events)

        return success_response(
            {"reply": reply, "intent": intent, "tokens": all_tokens, "events": matched_events},
            request=request,
        )


def _score_event(event: dict, tokens: list[str]) -> int:
    """Score an event against query tokens. Returns 0 if no match."""
    haystack = " ".join([
        (event.get("title") or ""),
        (event.get("event_type") or ""),
        (event.get("description") or ""),
    ]).lower()
    return sum(1 for t in tokens if len(t) > 2 and t in haystack)


def _filter_events(events: list[dict], tokens: list[str], want_free: bool | None = None) -> list[dict]:
    """Return up to 5 events ranked by keyword relevance, optionally filtered by is_free."""
    scored = []
    for e in events:
        if want_free is True and not e.get("is_free"):
            continue
        if want_free is False and e.get("is_free"):
            continue
        score = _score_event(e, tokens)
        scored.append((score, e))
    scored.sort(key=lambda x: x[0], reverse=True)
    # return top 5; if nothing matched return first 5 as general suggestions
    top = [e for _, e in scored if _[0] > 0][:5]
    return top if top else [e for _, e in scored[:5]]


def _classify_and_reply(
    message: str,
    tokens: list[str],
    history: list[dict],
    available_events: list[dict] | None = None,
) -> tuple[str, str, list[dict]]:
    """Map tokens to an intent bucket and return (intent, reply, events) triple."""
    events: list[dict] = []
    if available_events is None:
        available_events = []

    # greeting
    if any(t in tokens for t in ("hi", "hello", "hey", "namaste", "greetings", "hola")):
        return "greeting", "Namaste! I am Sansaar's assistant. I can help you find events, manage registration, learn about volunteering, or answer payment questions. What would you like to know?", events

    # event discovery - recommend real events when available
    is_event_intent = any(t in tokens for t in (
        "event", "events", "happening", "upcoming", "conference", "workshop",
        "seminar", "webinar", "festival", "recommend", "suggest", "select",
        "show", "list", "find", "looking", "interested",
    ))
    if is_event_intent:
        if any(t in tokens for t in ("create", "publish", "new", "organise", "organize", "host")):
            return "event_create", "To create an event, go to your Org Dashboard and click New Event. Fill in the details, add a cover image, set the date and location, then publish when ready.", events

        want_free: bool | None = None
        if any(t in tokens for t in ("free", "no cost")):
            want_free = True
        elif any(t in tokens for t in ("paid", "ticket", "priced")):
            want_free = False

        if available_events:
            events = _filter_events(available_events, tokens, want_free)
            if events:
                count = len(events)
                qualifier = "free " if want_free else ""
                reply = f"Here are {count} {qualifier}event{'s' if count != 1 else ''} that match your query. Click any to open the event page and register."
                return "event_recommend", reply, events

        # no events in context
        reply = "Browse all upcoming events on the Events page. Use the search bar for natural-language queries like 'free tech events in Kathmandu' or filter by category and date."
        return "event_discover", reply, events

    # registration
    if any(t in tokens for t in ("register", "registration", "ticket", "sign", "enrol", "enroll", "book", "attend", "join")):
        if any(t in tokens for t in ("cancel", "refund", "withdraw")):
            return "registration_cancel", "To cancel a registration, go to My Tickets, find the event, and click Cancel. Refund policies depend on the organiser. You can request a refund from the Finance section.", events
        if any(t in tokens for t in ("qr", "code", "scan", "check")):
            return "registration_qr", "Your QR code is on your ticket in My Tickets. Show it to event staff for check-in. It refreshes every 4 minutes for security.", events
        # if registering and events are available, show relevant ones
        if available_events:
            events = _filter_events(available_events, tokens)[:3]
        return "registration", "To register for an event, open the event page and click Register. For free events it is instant. For paid events you will be directed to checkout.", events

    # volunteer
    if any(t in tokens for t in ("volunteer", "volunteering", "shift", "help", "assist")):
        if any(t in tokens for t in ("apply", "application", "how", "sign")):
            return "volunteer_apply", "Browse volunteer roles under the Volunteer section. Click Apply on any role that interests you and leave a short message. The organiser will approve or reject your application.", events
        return "volunteer", "The Volunteer section shows all open roles for events you are attending. You can apply, track your hours, and download certificates after completing shifts.", events

    # payment
    if any(t in tokens for t in ("pay", "payment", "price", "cost", "fee", "refund", "invoice", "billing", "subscription", "plan", "upgrade")):
        if any(t in tokens for t in ("refund", "money", "back", "return")):
            return "payment_refund", "To request a refund, go to Finance > My Orders, open the order, and click Request Refund. Refunds are processed within 5-7 business days depending on your gateway.", events
        if any(t in tokens for t in ("plan", "upgrade", "starter", "pro", "enterprise", "ngo")):
            return "payment_plans", "Sansaar offers Free, Starter (NPR 999/mo), Pro (NPR 4,999/mo), NGO (free), and Enterprise (NPR 14,999/mo) plans. Higher plans reduce platform fees and unlock advanced features.", events
        return "payment", "Payments are handled via Khalti and eSewa for NPR transactions. Go to Finance > Billing to manage your subscription or view past orders.", events

    # organisation
    if any(t in tokens for t in ("org", "organisation", "organization", "workspace", "team", "member")):
        if any(t in tokens for t in ("create", "new", "start", "setup")):
            return "org_create", "To create an organisation, click New Org from your profile menu. Fill in your details, submit for verification, and our team will review within 24 hours.", events
        if any(t in tokens for t in ("member", "team", "invite", "add")):
            return "org_members", "You can invite team members from Org Settings. Members can have Owner, Admin, Manager, or Member roles with different permission levels.", events
        return "org", "Your organisation workspace gives you access to event management, member management, analytics, finance, and venue booking tools.", events

    # analytics
    if any(t in tokens for t in ("analytics", "report", "stats", "statistics", "data", "insight")):
        return "analytics", "Analytics are available per-event and at the platform level. View registrations, check-in rates, revenue breakdown, and attendee demographics from the Analytics section.", events

    # search
    if any(t in tokens for t in ("search", "discover", "explore")):
        return "search", "Use the Search page for natural-language queries powered by our NLP engine. Try queries like 'networking events this weekend' or 'volunteer at a music festival'.", events

    # help / about
    if any(t in tokens for t in ("help", "support", "contact", "about", "sansaar", "platform", "what")):
        return "help", "Sansaar is a multi-service event management platform. I can help with: finding events, registration, volunteering, payments, and organisation management. What would you like help with?", events

    # farewell
    if any(t in tokens for t in ("bye", "goodbye", "thanks", "thank", "great", "ok", "okay", "cool")):
        return "farewell", "You are welcome! Feel free to ask anything else about Sansaar. Have a great day!", events

    # fallback - suggest events if available
    if available_events:
        events = available_events[:4]
        return "unknown", f"I am not sure about '{message}', but here are some events you might be interested in. Ask me about registration, volunteering, or payments and I will help!", events

    return "unknown", f"I am not sure I understood '{message}'. I can help with events, registration, volunteering, payments, or organisation management. Could you rephrase?", events
