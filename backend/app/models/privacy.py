"""GDPR privacy models: data-subject requests (DSAR) and consent records."""
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class DSARType(str, enum.Enum):
    ACCESS = "access"            # Art.15 — right of access
    EXPORT = "export"            # Art.20 — data portability
    ERASURE = "erasure"          # Art.17 — right to be forgotten
    RESTRICTION = "restriction"  # Art.18 — restriction of processing
    RECTIFICATION = "rectification"  # Art.16 — correction


class DSARStatus(str, enum.Enum):
    RECEIVED = "received"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class DataSubjectRequest(Base):
    """A GDPR data-subject request and its handling trail."""
    __tablename__ = "data_subject_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    request_type = Column(Enum(DSARType), nullable=False)
    status = Column(Enum(DSARStatus), nullable=False, default=DSARStatus.RECEIVED)
    details = Column(Text, nullable=True)            # subject's free-text note
    resolution_notes = Column(Text, nullable=True)   # handler's note
    handled_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    # AML legal hold blocks erasure until the statutory retention period ends.
    legal_hold = Column(Boolean, default=False)
    due_at = Column(DateTime(timezone=True), nullable=True)  # 30-day response SLA
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class Consent(Base):
    """Versioned, time-stamped, revocable consent record (GDPR Art.7)."""
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = Column(String(100), nullable=False)          # e.g. 'kyc_processing', 'marketing'
    policy_version = Column(String(20), nullable=False, default="1.0")
    granted = Column(Boolean, nullable=False, default=True)
    granted_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
