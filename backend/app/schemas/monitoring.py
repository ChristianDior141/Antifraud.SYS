from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class DeviceResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    device_id: str
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    operating_system: Optional[str] = None
    browser: Optional[str] = None
    screen_resolution: Optional[str] = None
    is_trusted: bool
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    login_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    logout_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True


class LoginHistoryResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    email: Optional[str] = None
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    success: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SecurityEventResponse(BaseModel):
    id: int
    event_type: str
    severity: str
    user_id: Optional[int] = None
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    event_metadata: Optional[Any] = None
    resolved: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ActivityLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None
    action_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    result: Optional[str] = None
    details: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
