"""Shared rate limiter (OWASP ASVS V11 / brute-force mitigation)."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
