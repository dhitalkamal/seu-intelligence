"""Domain errors raised by intelligence use cases and never swallowed silently."""

from __future__ import annotations

from apps.common.api.exceptions import DomainError


class HealthScoreNotFoundError(DomainError):
    """No health score record exists for the given event."""

    http_status = 404
    code = "ERR_HEALTH_SCORE_NOT_FOUND"


class OptInRequiredError(DomainError):
    """Raised when a user has not opted in to the Who to Meet feature."""

    http_status = 403
    code = "ERR_CONNECTIONS_OPT_IN_REQUIRED"


class MatchNotFoundError(DomainError):
    """Raised when an attendee match record cannot be found."""

    http_status = 404
    code = "ERR_MATCH_NOT_FOUND"
