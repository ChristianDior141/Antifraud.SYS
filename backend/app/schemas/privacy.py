from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.privacy import DSARType, DSARStatus


class DSARCreate(BaseModel):
    request_type: DSARType
    details: Optional[str] = None


class DSARProcess(BaseModel):
    status: DSARStatus
    resolution_notes: Optional[str] = None


class DSARResponse(BaseModel):
    id: int
    user_id: int
    request_type: DSARType
    status: DSARStatus
    details: Optional[str] = None
    resolution_notes: Optional[str] = None
    legal_hold: bool
    due_at: Optional[datetime] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConsentUpsert(BaseModel):
    purpose: str
    granted: bool
    policy_version: str = "1.0"


class ConsentResponse(BaseModel):
    id: int
    purpose: str
    policy_version: str
    granted: bool
    granted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
