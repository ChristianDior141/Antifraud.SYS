from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, Float, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class AlertType(str, enum.Enum):
    STRUCTURING = "structuring"
    RAPID_MOVEMENT = "rapid_movement"
    HIGH_RISK_JURISDICTION = "high_risk_jurisdiction"
    UNUSUAL_FREQUENCY = "unusual_frequency"
    LARGE_CASH = "large_cash"
    VELOCITY_CHECK = "velocity_check"
    LAYERING = "layering"
    PEP_TRANSACTION = "pep_transaction"
    SANCTIONS_HIT = "sanctions_hit"


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    UNDER_INVESTIGATION = "under_investigation"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    SAR_FILED = "sar_filed"


class AMLAlert(Base):
    __tablename__ = "aml_alerts"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("client_profiles.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)

    alert_type = Column(Enum(AlertType), nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.OPEN)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    triggered_rule = Column(String(100), nullable=True)
    rule_parameters = Column(JSON, nullable=True)

    amount_involved = Column(Float, nullable=True)
    countries_involved = Column(JSON, nullable=True)

    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    investigation_notes = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    is_auto_generated = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    client = relationship("ClientProfile", back_populates="aml_alerts")
    transaction = relationship("Transaction", back_populates="aml_alerts")
