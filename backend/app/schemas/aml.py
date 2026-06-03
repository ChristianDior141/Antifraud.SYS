from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime
from app.models.aml import AlertType, AlertSeverity, AlertStatus


class AMLAlertResponse(BaseModel):
    id: int
    client_id: int
    transaction_id: Optional[int] = None
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    title: str
    description: str
    triggered_rule: Optional[str] = None
    amount_involved: Optional[float] = None
    countries_involved: Optional[List[str]] = None
    investigation_notes: Optional[str] = None
    is_auto_generated: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AMLAlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    investigation_notes: Optional[str] = None
    resolution_notes: Optional[str] = None
    assigned_to: Optional[int] = None


class AMLRuleConfig(BaseModel):
    rule_name: str
    threshold_amount: Optional[float] = None
    threshold_count: Optional[int] = None
    time_window_hours: Optional[int] = None
    risk_countries: Optional[List[str]] = None
    is_active: bool = True
