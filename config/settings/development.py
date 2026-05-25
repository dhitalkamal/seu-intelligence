"""Development settings for the intelligence-service: debug on, HS256 JWT."""

from __future__ import annotations

from decouple import config

from .base import *  # noqa: F401, F403

DEBUG = True

# HS256 for local dev -- no RSA key files required
SIMPLE_JWT = {
    **SIMPLE_JWT,  # noqa: F405
    "ALGORITHM": "HS256",
    "SIGNING_KEY": config("JWT_SECRET_KEY", default=SECRET_KEY),  # noqa: F405
    "VERIFYING_KEY": "",
}
