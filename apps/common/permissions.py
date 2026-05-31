"""Custom DRF permission classes for role-based access control."""

from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.request import Request


class IsSuperAdminFromAllowedIP(BasePermission):
    """Allow access only to staff users whose IP is in SUPERADMIN_ALLOWED_IPS."""

    def has_permission(self, request: Request, view: object) -> bool:
        """Return True if user is staff and their IP is whitelisted."""
        if not getattr(request.user, "is_authenticated", False):
            return False
        if not getattr(request.user, "is_staff", False):
            return False
        allowed: list[str] = getattr(settings, "SUPERADMIN_ALLOWED_IPS", [])
        if not allowed:
            return True
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.META.get("REMOTE_ADDR", "")
        return client_ip in allowed


class IsOrgRole(BasePermission):
    """Base class for org-role permission checks using JWT org_roles claim."""

    allowed_roles: list[str] = []

    def has_permission(self, request: Request, view: object) -> bool:
        """Check if user has required org role."""
        org_id = self._extract_org_id(request, view)
        if not org_id:
            return False
        org_roles = self._get_org_roles(request)
        return org_roles.get(str(org_id)) in self.allowed_roles

    def _extract_org_id(self, request: Request, view: object) -> str | None:
        """Try multiple sources for the org ID."""
        return (
            getattr(view, "org_id", None)
            or (view.kwargs.get("org_id") if hasattr(view, "kwargs") else None)
            or (view.kwargs.get("organization_id") if hasattr(view, "kwargs") else None)
            or request.data.get("organization_id")
            or request.query_params.get("organization_id")
        )

    def _get_org_roles(self, request: Request) -> dict[str, str]:
        """Extract org_roles from JWT token payload."""
        token = getattr(request.user, "token", None)
        if token and hasattr(token, "payload"):
            return token.payload.get("org_roles", {})
        if hasattr(request.user, "org_roles"):
            return request.user.org_roles
        return {}


class IsOrgOwner(IsOrgRole):
    """Only org owners."""

    allowed_roles = ["owner"]


class IsOrgAdmin(IsOrgRole):
    """Org owners and admins."""

    allowed_roles = ["owner", "admin"]


class IsOrgManager(IsOrgRole):
    """Org owners, admins, and managers."""

    allowed_roles = ["owner", "admin", "manager"]


class IsOrgMember(IsOrgRole):
    """Any active org member."""

    allowed_roles = ["owner", "admin", "manager", "member"]
