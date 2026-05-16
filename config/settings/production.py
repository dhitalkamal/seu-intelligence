"""Production settings for the intelligence-service: debug off, RS256 JWT."""
from __future__ import annotations

from decouple import config

from .base import *  # noqa: F401, F403

DEBUG = False

SIMPLE_JWT = {
    **SIMPLE_JWT,  # noqa: F405
    "ALGORITHM": "RS256",
    # non-IAM services verify tokens only -- no private key needed
    "SIGNING_KEY": "",
    "VERIFYING_KEY": config("JWT_PUBLIC_KEY").replace("\\n", "\n"),
}
