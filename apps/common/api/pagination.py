"""Standard pagination class used across all list endpoints."""

from __future__ import annotations

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.common.api.responses import _meta


class StandardPagination(PageNumberPagination):
    """Page-number pagination that returns the project meta envelope."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data: list) -> Response:
        """Wrap results in the standard {data, error, meta} envelope."""
        return Response(
            {
                "data": data,
                "error": None,
                "meta": {
                    **_meta(),
                    "pagination": {
                        "page": self.page.number,
                        "per_page": self.page.paginator.per_page,
                        "total": self.page.paginator.count,
                        "total_pages": self.page.paginator.num_pages,
                        "has_next": self.get_next_link() is not None,
                        "has_prev": self.get_previous_link() is not None,
                    },
                },
            }
        )

    def get_paginated_response_schema(self, schema: dict) -> dict:
        """OpenAPI schema for the paginated envelope."""
        return {
            "type": "object",
            "required": ["data", "error", "meta"],
            "properties": {
                "data": schema,
                "error": {"type": "object", "nullable": True},
                "meta": {
                    "type": "object",
                    "properties": {
                        "request_id": {"type": "string"},
                        "timestamp": {"type": "string"},
                        "pagination": {
                            "type": "object",
                            "properties": {
                                "page": {"type": "integer"},
                                "per_page": {"type": "integer"},
                                "total": {"type": "integer"},
                                "total_pages": {"type": "integer"},
                                "has_next": {"type": "boolean"},
                                "has_prev": {"type": "boolean"},
                            },
                        },
                    },
                },
            },
        }
