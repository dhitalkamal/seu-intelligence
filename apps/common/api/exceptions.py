"""RFC 9457 Problem Details exception handler and base domain error class."""
from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class DomainError(Exception):
    """Base for all domain-level errors.

    Subclasses set `code` (SCREAMING_SNAKE) and `http_status`.
    The exception handler maps these directly to RFC 9457 responses.
    """

    http_status: int = 400
    code: str = "DOMAIN_ERROR"

    def __init__(self, detail: str) -> None:
        """Store the human-readable problem detail."""
        self.detail = detail
        super().__init__(detail)


def _problem(
    type_slug: str,
    title: str,
    http_status: int,
    detail: str,
    code: str,
    extra: dict | None = None,
) -> Response:
    """Build an RFC 9457 Problem Details response body."""
    body: dict = {
        "type": f"/errors/{type_slug}",
        "title": title,
        "status": http_status,
        "detail": detail,
        "code": code,
    }
    if extra:
        body.update(extra)
    return Response(body, status=http_status, content_type="application/problem+json")


def _detail(data: dict | list | str, fallback: str) -> str:
    """Extract a readable string from whatever DRF puts in response.data."""
    if isinstance(data, dict):
        return str(data.get("detail", fallback))
    if isinstance(data, list) and data:
        return str(data[0])
    return str(data) if data else fallback


def api_exception_handler(exc: Exception, context: dict) -> Response | None:
    """Convert DRF and domain exceptions into RFC 9457 Problem Details."""
    if isinstance(exc, DomainError):
        return _problem(
            type_slug=exc.code.lower().replace("_", "-"),
            title=exc.code.replace("_", " ").title(),
            http_status=exc.http_status,
            detail=exc.detail,
            code=exc.code,
        )

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    http_status = response.status_code

    if http_status == status.HTTP_400_BAD_REQUEST:
        return _problem(
            type_slug="validation-error",
            title="Validation Error",
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The submitted data failed validation.",
            code="VALIDATION_ERROR",
            extra={"errors": data},
        )

    if http_status == status.HTTP_401_UNAUTHORIZED:
        return _problem(
            type_slug="unauthorized",
            title="Unauthorized",
            http_status=401,
            detail=_detail(data, "Authentication credentials were not provided."),
            code="UNAUTHORIZED",
        )

    if http_status == status.HTTP_403_FORBIDDEN:
        return _problem(
            type_slug="forbidden",
            title="Forbidden",
            http_status=403,
            detail=_detail(data, "You do not have permission to perform this action."),
            code="FORBIDDEN",
        )

    if http_status == status.HTTP_404_NOT_FOUND:
        return _problem(
            type_slug="not-found",
            title="Not Found",
            http_status=404,
            detail=_detail(data, "The requested resource was not found."),
            code="NOT_FOUND",
        )

    if http_status == status.HTTP_405_METHOD_NOT_ALLOWED:
        return _problem(
            type_slug="method-not-allowed",
            title="Method Not Allowed",
            http_status=405,
            detail=_detail(data, "Method not allowed."),
            code="METHOD_NOT_ALLOWED",
        )

    if http_status == status.HTTP_429_TOO_MANY_REQUESTS:
        return _problem(
            type_slug="too-many-requests",
            title="Too Many Requests",
            http_status=429,
            detail=_detail(data, "Request was throttled."),
            code="TOO_MANY_REQUESTS",
        )

    return _problem(
        type_slug="api-error",
        title="API Error",
        http_status=http_status,
        detail=_detail(data, "An unexpected error occurred."),
        code="API_ERROR",
    )
