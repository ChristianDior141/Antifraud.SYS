from datetime import datetime, timedelta
from typing import Any, Union, Optional
from uuid import uuid4
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (
        expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    # jti enables per-token revocation (logout / forced sign-out).
    payload = {"exp": expire, "sub": str(subject), "type": "access", "jti": uuid4().hex}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"exp": expire, "sub": str(subject), "type": "refresh", "jti": uuid4().hex}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Return the full JWT payload, or None if invalid/expired."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


def verify_token(token: str, expected_type: Optional[str] = None) -> Optional[str]:
    """Decode a JWT and return its subject.

    When ``expected_type`` is given (e.g. "access" or "refresh") the token's
    ``type`` claim must match — this prevents a refresh token from being used
    as an access token and vice-versa (OWASP ASVS V3.5).
    """
    payload = decode_token(token)
    if payload is None:
        return None
    if expected_type is not None and payload.get("type") != expected_type:
        return None
    return payload.get("sub")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
