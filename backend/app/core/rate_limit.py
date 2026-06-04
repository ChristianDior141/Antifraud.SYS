"""Shared rate limiter (OWASP ASVS V11 / brute-force mitigation).

Uses a configurable storage backend: in-memory for a single instance/tests,
or Redis so the limit is enforced consistently across horizontally-scaled
instances (removes a scaling SPOF).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
)
