from pydantic import BaseModel, validator
from typing import Optional, List, Any
from datetime import datetime, date
from app.models.client import KYCStatus, RiskLevel


class ClientProfileBase(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    country_of_birth: Optional[str] = None
    country_of_residence: Optional[str] = None
    phone_number: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    id_expiry_date: Optional[date] = None
    id_issuing_country: Optional[str] = None
    occupation: Optional[str] = None
    employer_name: Optional[str] = None
    annual_income_range: Optional[str] = None
    source_of_funds: Optional[str] = None
    source_of_wealth: Optional[str] = None
    expected_monthly_transaction_volume: Optional[float] = None


class ClientProfileCreate(ClientProfileBase):
    pass


class ClientProfileUpdate(ClientProfileBase):
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class ClientProfileResponse(ClientProfileBase):
    id: int
    user_id: int
    kyc_status: KYCStatus
    risk_level: RiskLevel
    risk_score: float
    is_pep: bool
    is_sanctioned: bool
    is_high_risk_country: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ClientListResponse(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str
    nationality: Optional[str] = None
    kyc_status: KYCStatus
    risk_level: RiskLevel
    risk_score: float
    is_pep: bool
    created_at: datetime

    class Config:
        from_attributes = True
