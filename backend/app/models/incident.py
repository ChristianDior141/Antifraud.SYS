"""
Incident Management & False Positive Analysis models.

Every AML alert is bridged to exactly one IncidentTicket. Analysts investigate
the ticket (comments, assignments), perform RiskAssessments, and finally
classify it as a real incident or a false positive. False positives capture a
root cause and a rule responsible, feeding the detection-rule tuning loop.
"""
import enum
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.client import RiskLevel  # reuse low/medium/high/critical


class TicketStatus(str, enum.Enum):
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    ESCALATED = "escalated"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentClassification(str, enum.Enum):
    REAL_INCIDENT = "real_incident"
    FALSE_POSITIVE = "false_positive"


class FalsePositiveReason(str, enum.Enum):
    THRESHOLD_TOO_SENSITIVE = "threshold_too_sensitive"
    INCORRECT_CORRELATION_RULE = "incorrect_correlation_rule"
    WHITELISTED_ACTIVITY = "whitelisted_activity"
    LEGITIMATE_USER_BEHAVIOR = "legitimate_user_behavior"
    DATA_QUALITY_ISSUE = "data_quality_issue"
    CONFIGURATION_ERROR = "configuration_error"
    OTHER = "other"


class IncidentTicket(Base):
    __tablename__ = "incident_tickets"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("aml_alerts.id"), unique=True, nullable=False)
    client_id = Column(Integer, ForeignKey("client_profiles.id"), nullable=True)
    detection_rule_id = Column(Integer, ForeignKey("detection_rules.id"), nullable=True)

    alert_source = Column(String(100), default="AML Monitor")
    alert_type = Column(String(100), nullable=True)

    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIUM, nullable=False)
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.MEDIUM, nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.NEW, nullable=False)
    classification = Column(Enum(IncidentClassification), nullable=True)

    assigned_analyst_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    first_assigned_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    alert = relationship("AMLAlert")
    detection_rule = relationship("DetectionRule")
    assigned_analyst = relationship("User", foreign_keys=[assigned_analyst_id])

    comments = relationship(
        "IncidentComment", back_populates="ticket", cascade="all, delete-orphan",
        order_by="IncidentComment.created_at",
    )
    assignments = relationship(
        "IncidentAssignment", back_populates="ticket", cascade="all, delete-orphan",
        order_by="IncidentAssignment.created_at",
    )
    risk_assessments = relationship(
        "RiskAssessment", back_populates="ticket", cascade="all, delete-orphan",
        order_by="RiskAssessment.created_at",
    )
    false_positive = relationship(
        "FalsePositive", back_populates="ticket", uselist=False,
        cascade="all, delete-orphan",
    )


class IncidentComment(Base):
    __tablename__ = "incident_comments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("incident_tickets.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("IncidentTicket", back_populates="comments")
    author = relationship("User", foreign_keys=[author_id])


class IncidentAssignment(Base):
    __tablename__ = "incident_assignments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("incident_tickets.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("IncidentTicket", back_populates="assignments")
    assignee = relationship("User", foreign_keys=[assigned_to])
    assigner = relationship("User", foreign_keys=[assigned_by])


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("incident_tickets.id"), nullable=False)
    assessor_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    risk_level = Column(Enum(RiskLevel), nullable=False)
    business_impact = Column(Text, nullable=True)
    financial_impact = Column(Float, nullable=True)
    technical_impact = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)        # 0-100
    recommended_action = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("IncidentTicket", back_populates="risk_assessments")
    assessor = relationship("User", foreign_keys=[assessor_id])


class FalsePositive(Base):
    __tablename__ = "false_positives"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("incident_tickets.id"), unique=True, nullable=False)
    classified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    detection_rule_id = Column(Integer, ForeignKey("detection_rules.id"), nullable=True)

    reason = Column(Enum(FalsePositiveReason), nullable=False)
    root_cause = Column(Text, nullable=True)
    source_system = Column(String(100), nullable=True)
    analyst_comments = Column(Text, nullable=True)
    suggested_rule_tuning = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("IncidentTicket", back_populates="false_positive")
    detection_rule = relationship("DetectionRule")
    classifier = relationship("User", foreign_keys=[classified_by])
