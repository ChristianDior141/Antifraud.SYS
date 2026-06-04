from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
import phonenumbers
from app.models.user import UserRole


def validate_phone_e164(v: str) -> str:
    try:
        num = phonenumbers.parse(v, None)  # international format with leading +
        if not phonenumbers.is_valid_number(num):
            raise ValueError
        return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        raise ValueError("Invalid phone number; use international format, e.g. +14155552671")

# Server-side password policy (ISO 27001 A.9.4.3 / OWASP ASVS V2.1).
_SPECIAL_CHARS = set("!@#$%^&*()-_=+[]{};:,.<>?/|~`")


def validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not any(c.isupper() for c in v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one digit")
    if not any(c in _SPECIAL_CHARS for c in v):
        raise ValueError("Password must contain at least one special character")
    return v


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.CLIENT


class UserCreate(UserBase):
    password: str
    phone_number: str  # required, international format

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        return validate_password_strength(v)

    @field_validator("phone_number")
    @classmethod
    def phone_valid(cls, v):
        return validate_phone_e164(v)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class UserResponse(UserBase):
    id: int
    phone_number: Optional[str] = None
    is_active: bool
    is_verified: bool
    mfa_enabled: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    mfa_code: Optional[str] = None  # required when the account has MFA enabled


class MFAVerify(BaseModel):
    code: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordReset(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        return validate_password_strength(v)
