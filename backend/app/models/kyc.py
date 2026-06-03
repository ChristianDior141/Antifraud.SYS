from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, Boolean, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class KYCForm(Base):
    __tablename__ = "kyc_forms"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("client_profiles.id"), unique=True, nullable=False)

    # Section 1: Personal
    purpose_of_account = Column(String(255), nullable=True)
    business_type = Column(String(100), nullable=True)
    industry_sector = Column(String(100), nullable=True)

    # Section 2: Financial profile
    estimated_annual_income = Column(String(50), nullable=True)
    primary_source_of_funds = Column(String(100), nullable=True)
    other_source_of_funds = Column(Text, nullable=True)

    # Section 3: Transaction expectations
    countries_of_transaction = Column(JSON, nullable=True)
    expected_monthly_volume = Column(Float, nullable=True)
    max_single_transaction = Column(Float, nullable=True)

    # Section 4: Declarations
    is_us_person = Column(Boolean, default=False)
    has_other_citizenship = Column(Boolean, default=False)
    other_citizenships = Column(JSON, nullable=True)
    is_beneficial_owner = Column(Boolean, default=True)
    beneficial_owner_details = Column(Text, nullable=True)
    agrees_to_terms = Column(Boolean, default=False)
    agrees_to_data_processing = Column(Boolean, default=False)

    # Submission
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    is_complete = Column(Boolean, default=False)
    completion_percentage = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    client = relationship("ClientProfile", back_populates="kyc_form")
