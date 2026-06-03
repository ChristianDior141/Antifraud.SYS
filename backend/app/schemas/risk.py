from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class RiskScoreResponse(BaseModel):
    id: int
    client_id: int
    total_score: float
    risk_level: str
    personal_risk_score: float
    transaction_risk_score: float
    behavioral_risk_score: float
    geographic_risk_score: float
    document_risk_score: float
    risk_factors: Optional[Dict[str, Any]] = None
    pep_flag: bool
    sanctions_flag: bool
    high_risk_country_flag: bool
    unusual_transaction_flag: bool
    calculated_at: datetime

    class Config:
        from_attributes = True


class RiskFactorDetail(BaseModel):
    factor: str
    score: float
    weight: float
    description: str
    is_flagged: bool


class RiskAssessmentReport(BaseModel):
    client_id: int
    total_score: float
    risk_level: str
    factors: List[RiskFactorDetail]
    recommendation: str
    calculated_at: datetime
