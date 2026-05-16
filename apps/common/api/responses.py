"""Standard response helpers following the project API contract."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from rest_framework.response import Response


def _meta(request: Any = None) -> dict:
    """Build the standard meta block with request_id and timestamp."""
    request_id = getattr(request, "request_id", None) or str(uuid.uuid4())
    return {
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def success_response(
    data: dict | list,
    request: Any = None,
    status: int = 200,
) -> Response:
    """Wrap a resource in the standard success envelope."""
    return Response({"data": data, "error": None, "meta": _meta(request)}, status=status)


def created_response(data: dict, request: Any = None) -> Response:
    """Convenience wrapper for 201 Created responses."""
    return success_response(data, request=request, status=201)


def error_response(
    code: str,
    message: str,
    details: Any = None,
    http_status: int = 400,
    request: Any = None,
) -> Response:
    """Build an error response using the standard envelope format."""
    return Response(
        {
            "data": None,
            "error": {"code": code, "message": message, "details": details},
            "meta": _meta(request),
        },
        status=http_status,
    )
