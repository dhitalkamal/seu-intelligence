"""Standard response helpers following the project API contract."""
from __future__ import annotations

from rest_framework.response import Response


def success_response(data: dict | list, status: int = 200) -> Response:
    """Wrap a resource or data dict in the standard data envelope."""
    return Response({"data": data}, status=status)


def created_response(data: dict) -> Response:
    """Convenience wrapper for 201 Created responses."""
    return success_response(data, status=201)
