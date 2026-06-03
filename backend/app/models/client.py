from sqlalchemy import (
    Column, Integer, String, Boolean, Enum, DateTime, Text,
    Date, Float, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base
from app.core.crypto import EncryptedString


class KYCStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_UPDATE = "requires_update"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClientProfile(Base):
    __tablename__ = "client_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    nationality = Column(String(100), nullable=True)
    country_of_birth = Column(String(100), nullable=True)
    country_of_residence = Column(String(100), nullable=True)

    # Contact Information
    phone_number = Column(EncryptedString, nullable=True)  # PII — encrypted at rest
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state_province = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)

    # Identity
    id_type = Column(String(50), nullable=True)
    id_number = Column(EncryptedString, nullable=True)  # PII — encrypted at rest
    id_expiry_date = Column(Date, nullable=True)
    id_issuing_country = Column(String(100), nullable=True)

    # Financial Information
    occupation = Column(String(255), nullable=True)
    employer_name = Column(String(255), nullable=True)
    annual_income_range = Column(String(50), nullable=True)
    source_of_funds = Column(EncryptedString, nullable=True)   # encrypted at rest
    source_of_wealth = Column(EncryptedString, nullable=True)  # encrypted at rest
    expected_monthly_transaction_volume = Column(Float, nullable=True)
    expected_transaction_types = Column(JSON, nullable=True)

    # AML/KYC Flags
    is_pep = Column(Boolean, default=False)
    pep_details = Column(EncryptedString, nullable=True)  # PII — encrypted at rest
    is_sanctioned = Column(Boolean, default=False)
    is_high_risk_country = Column(Boolean, default=False)

    # Status
    kyc_status = Column(Enum(KYCStatus), default=KYCStatus.NOT_STARTED)
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.LOW)
    risk_score = Column(Float, default=0.0)

    # Metadata
    ip_address = Column(String(45), nullable=True)
    device_fingerprint = Column(String(255), nullable=True)

    # GDPR data lifecycle
    retention_until = Column(DateTime(timezone=True), nullable=True)  # purge/anonymize after
    processing_restricted = Column(Boolean, default=False)            # Art.18 restriction
    anonymized_at = Column(DateTime(timezone=True), nullable=True)    # set on erasure

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="client_profile")
    documents = relationship("Document", back_populates="client")
    kyc_form = relationship("KYCForm", back_populates="client", uselist=False)
    risk_scores = relationship("RiskScore", back_populates="client")
    transactions = relationship("Transaction", back_populates="client")
    aml_alerts = relationship("AMLAlert", back_populates="client")
    reviews = relationship("Review", back_populates="client")
