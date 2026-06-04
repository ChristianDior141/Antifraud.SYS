"""Device intelligence, sessions, login/IP history, activity & security events."""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from app.core.database import Base


class Device(Base):
    """A device a user has authenticated from."""
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("user_id", "device_id", name="uq_device_user"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    device_id = Column(String(128), nullable=False)        # client-generated stable id
    device_name = Column(String(255), nullable=True)
    device_type = Column(String(50), nullable=True)        # desktop / mobile / tablet
    operating_system = Column(String(100), nullable=True)
    browser = Column(String(100), nullable=True)
    user_agent = Column(Text, nullable=True)
    screen_resolution = Column(String(50), nullable=True)
    is_trusted = Column(Boolean, default=False)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now())


class UserSession(Base):
    """An authenticated session (login → logout)."""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_jti = Column(String(64), index=True, nullable=True)
    device_id = Column(String(128), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    login_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())
    logout_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)


class LoginHistory(Base):
    """Every login attempt (success or failure)."""
    __tablename__ = "login_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    email = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    device_id = Column(String(128), nullable=True)
    user_agent = Column(Text, nullable=True)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IPHistory(Base):
    """Distinct IP addresses seen per user."""
    __tablename__ = "ip_history"
    __table_args__ = (UniqueConstraint("user_id", "ip_address", name="uq_ip_user"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    ip_address = Column(String(45), nullable=False)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now())


class UserActivityLog(Base):
    """Business-action activity timeline (tickets, risk assessments, FP reviews, …)."""
    __tablename__ = "user_activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    username = Column(String(255), nullable=True)
    role = Column(String(50), nullable=True)
    action_type = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)
    device_id = Column(String(128), nullable=True)
    result = Column(String(20), default="success")
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SecurityEvent(Base):
    """Automatically detected security signals."""
    __tablename__ = "security_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False)   # new_device, new_ip, multiple_failed_logins, rapid_ip_change, suspicious_activity
    severity = Column(String(20), default="medium")     # low / medium / high / critical
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    device_id = Column(String(128), nullable=True)
    event_metadata = Column(JSON, nullable=True)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
