"""
Detection Rule registry and tuning history.

Each AML monitoring rule (keyed by the same `triggered_rule` code used by the
AML monitor) has a row here so the platform can score rule effectiveness and
record tuning changes driven by false-positive analysis.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class DetectionRule(Base):
    __tablename__ = "detection_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_code = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    alert_type = Column(String(100), nullable=True)
    parameters = Column(JSON, nullable=True)        # current threshold parameters
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tuning_history = relationship(
        "RuleTuningHistory", back_populates="rule", cascade="all, delete-orphan"
    )


class RuleTuningHistory(Base):
    __tablename__ = "rule_tuning_history"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("detection_rules.id"), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    false_positive_id = Column(Integer, ForeignKey("false_positives.id"), nullable=True)

    version = Column(Integer, nullable=False)
    change_description = Column(Text, nullable=True)
    old_parameters = Column(JSON, nullable=True)
    new_parameters = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    rule = relationship("DetectionRule", back_populates="tuning_history")
