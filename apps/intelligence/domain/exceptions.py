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


class ReportJobNotFoundError(DomainError):
    """Raised when a report job record cannot be found."""

    http_status = 404
    code = "ERR_REPORT_JOB_NOT_FOUND"


class ReportJobNotCompletedError(DomainError):
    """Raised when a download is requested for a job that has not completed."""

    http_status = 409
    code = "ERR_REPORT_JOB_NOT_COMPLETED"


class ScheduledReportNotFoundError(DomainError):
    """Raised when a scheduled report record cannot be found."""

    http_status = 404
    code = "ERR_SCHEDULED_REPORT_NOT_FOUND"
