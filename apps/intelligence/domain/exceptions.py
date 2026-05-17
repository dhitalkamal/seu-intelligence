"""Domain errors raised by intelligence use cases and never swallowed silently."""

from __future__ import annotations

from apps.common.api.exceptions import DomainError


class HealthScoreNotFoundError(DomainError):
    """No health score record exists for the given event."""

    http_status = 404
    code = "ERR_HEALTH_SCORE_NOT_FOUND"
