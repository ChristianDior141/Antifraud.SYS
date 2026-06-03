from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class RuleTuningHistoryResponse(BaseModel):
    id: int
    rule_id: int
    changed_by: Optional[int] = None
    false_positive_id: Optional[int] = None
    version: int
    change_description: Optional[str] = None
    old_parameters: Optional[Dict[str, Any]] = None
    new_parameters: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DetectionRuleStats(BaseModel):
    total_alerts: int
    confirmed_incidents: int
    false_positives: int
    false_positive_rate: float        # 0-100 (%)
    effectiveness_score: float        # 0-100


class DetectionRuleResponse(BaseModel):
    id: int
    rule_code: str
    name: str
    description: Optional[str] = None
    alert_type: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    version: int
    is_active: bool
    created_at: datetime
    stats: Optional[DetectionRuleStats] = None

    class Config:
        from_attributes = True


class DetectionRuleDetail(DetectionRuleResponse):
    tuning_history: List[RuleTuningHistoryResponse] = []
    suggested_improvements: List[str] = []


class RuleTuneRequest(BaseModel):
    new_parameters: Dict[str, Any]
    change_description: str
    is_active: Optional[bool] = None
