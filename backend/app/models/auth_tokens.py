"""Token revocation denylist and password-reset tokens."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class RevokedToken(Base):
    """A revoked JWT (by jti). Checked on every authenticated request."""
    __tablename__ = "revoked_tokens"

    jti = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # for periodic cleanup
    revoked_at = Column(DateTime(timezone=True), server_default=func.now())


class PasswordResetToken(Base):
    """Single-use, time-limited password reset token (stored hashed)."""
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
