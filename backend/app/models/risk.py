from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, Float, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class RiskCategory(str, enum.Enum):
    PERSONAL = "personal"
    TRANSACTION = "transaction"
    BEHAVIORAL = "behavioral"
    GEOGRAPHIC = "geographic"
    DOCUMENT = "document"


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("client_profiles.id"), nullable=False)

    # Aggregate
    total_score = Column(Float, default=0.0)
    risk_level = Column(String(20), nullable=False, default="low")

    # Component scores
    personal_risk_score = Column(Float, default=0.0)
    transaction_risk_score = Column(Float, default=0.0)
    behavioral_risk_score = Column(Float, default=0.0)
    geographic_risk_score = Column(Float, default=0.0)
    document_risk_score = Column(Float, default=0.0)

    # Factor breakdown
    risk_factors = Column(JSON, nullable=True)
    calculation_details = Column(JSON, nullable=True)

    # Flags
    pep_flag = Column(Boolean, default=False)
    sanctions_flag = Column(Boolean, default=False)
    high_risk_country_flag = Column(Boolean, default=False)
    unusual_transaction_flag = Column(Boolean, default=False)

    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    calculated_by = Column(String(50), default="system")

    client = relationship("ClientProfile", back_populates="risk_scores")
