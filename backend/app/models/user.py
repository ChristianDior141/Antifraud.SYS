from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base
from app.core.crypto import EncryptedString


class UserRole(str, enum.Enum):
    CLIENT = "client"
    COMPLIANCE_OFFICER = "compliance_officer"
    RISK_ANALYST = "risk_analyst"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CLIENT, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(EncryptedString, nullable=True)  # encrypted at rest
    mfa_backup_codes = Column(JSON, nullable=True)        # list of hashed backup codes
    last_login = Column(DateTime(timezone=True), nullable=True)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    client_profile = relationship("ClientProfile", back_populates="user", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    reviews = relationship("Review", back_populates="reviewer")
