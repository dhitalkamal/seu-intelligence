"""Middleware that stamps every request with a unique ID."""

from __future__ import annotations

import uuid

from django.http import HttpRequest, HttpResponse


class RequestContextMiddleware:
    """Attach a request_id to every request and echo it in the response header."""

    def __init__(self, get_response) -> None:
        """Store the next middleware or view callable."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Stamp request_id before the view, echo it in the response."""
        request.request_id = request.META.get("HTTP_X_REQUEST_ID") or str(uuid.uuid4())
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response
