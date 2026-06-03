from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.client import RiskLevel
from app.models.incident import (
    TicketStatus, TicketPriority, IncidentClassification, FalsePositiveReason,
)


# ---- Comments / assignments / assessments -------------------------------

class IncidentCommentResponse(BaseModel):
    id: int
    ticket_id: int
    author_id: Optional[int] = None
    comment: str
    created_at: datetime

    class Config:
        from_attributes = True


class IncidentCommentCreate(BaseModel):
    comment: str


class IncidentAssignmentResponse(BaseModel):
    id: int
    ticket_id: int
    assigned_to: Optional[int] = None
    assigned_by: Optional[int] = None
    note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AssignRequest(BaseModel):
    assigned_to: int
    note: Optional[str] = None


class RiskAssessmentResponse(BaseModel):
    id: int
    ticket_id: int
    assessor_id: Optional[int] = None
    risk_level: RiskLevel
    business_impact: Optional[str] = None
    financial_impact: Optional[float] = None
    technical_impact: Optional[str] = None
    confidence_score: Optional[float] = None
    recommended_action: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RiskAssessmentCreate(BaseModel):
    risk_level: RiskLevel
    business_impact: Optional[str] = None
    financial_impact: Optional[float] = None
    technical_impact: Optional[str] = None
    confidence_score: Optional[float] = None
    recommended_action: Optional[str] = None


class FalsePositiveResponse(BaseModel):
    id: int
    ticket_id: int
    classified_by: Optional[int] = None
    detection_rule_id: Optional[int] = None
    reason: FalsePositiveReason
    root_cause: Optional[str] = None
    source_system: Optional[str] = None
    analyst_comments: Optional[str] = None
    suggested_rule_tuning: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---- Tickets ------------------------------------------------------------

class IncidentTicketResponse(BaseModel):
    id: int
    alert_id: int
    client_id: Optional[int] = None
    detection_rule_id: Optional[int] = None
    alert_source: Optional[str] = None
    alert_type: Optional[str] = None
    priority: TicketPriority
    risk_level: RiskLevel
    status: TicketStatus
    classification: Optional[IncidentClassification] = None
    assigned_analyst_id: Optional[int] = None
    resolution_notes: Optional[str] = None
    first_assigned_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class IncidentTicketDetail(IncidentTicketResponse):
    comments: List[IncidentCommentResponse] = []
    assignments: List[IncidentAssignmentResponse] = []
    risk_assessments: List[RiskAssessmentResponse] = []
    false_positive: Optional[FalsePositiveResponse] = None


class StatusUpdate(BaseModel):
    status: TicketStatus
    resolution_notes: Optional[str] = None


class ClassifyRequest(BaseModel):
    classification: IncidentClassification
    resolution_notes: Optional[str] = None
    # required when classification == false_positive
    reason: Optional[FalsePositiveReason] = None
    root_cause: Optional[str] = None
    source_system: Optional[str] = None
    analyst_comments: Optional[str] = None
    suggested_rule_tuning: Optional[str] = None
