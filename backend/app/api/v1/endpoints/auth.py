import hashlib
import secrets as _secrets
import pyotp
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import (
    verify_password, get_password_hash, create_access_token, create_refresh_token,
    verify_token, decode_token,
)
from app.core.deps import get_current_user, security
from app.models.user import User, UserRole
from app.models.auth_tokens import RevokedToken, PasswordResetToken
from app.services.audit_service import record_audit
from app.services import monitoring_service as mon
from app.schemas.user import (
    UserCreate, UserLogin, TokenResponse, UserResponse, UserUpdate, RefreshRequest,
    MFAVerify, PasswordReset, PasswordResetConfirm,
)

MFA_ISSUER = "Antifraud.SYS"


def _gen_backup_codes(n: int = 8) -> list:
    return [_secrets.token_hex(4) for _ in range(n)]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime) -> datetime:
    """Normalise a possibly-naive datetime (e.g. from SQLite) to UTC-aware."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_in: UserCreate, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Phone uniqueness (already normalised to E.164 by the schema validator)
    dup_phone = await db.execute(select(User).where(User.phone_number == user_in.phone_number))
    if dup_phone.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Phone number already registered")

    user = User(
        email=user_in.email,
        phone_number=user_in.phone_number,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
    )
    db.add(user)
    await db.flush()

    await mon.upsert_device(db, user.id, request)
    await record_audit(
        db, action="USER_REGISTERED", user_id=user.id, resource_type="user",
        resource_id=user.id, description=f"New user registered: {user.email}",
        username=user.email, user_role=user.role.value if user.role else None,
        ip_address=mon.client_ip(request), device_id=mon.device_id_from_request(request),
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(credentials: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()
    client_ip = request.client.host if request.client else None

    # Account lockout: reject while a temporary lock is still active (A.9.4.2).
    if user and user.locked_until and _as_aware(user.locked_until) > _utcnow():
        await record_audit(
            db, action="LOGIN_BLOCKED_LOCKED", user_id=user.id, resource_type="user",
            resource_id=user.id, description="Login attempt while account locked",
            ip_address=client_ip, user_agent=request.headers.get("user-agent"),
            status="blocked",
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to repeated failed logins. Try again later.",
        )

    if not user or not verify_password(credentials.password, user.hashed_password):
        await mon.record_failed_login(db, credentials.email, request,
                                      user_id=user.id if user else None)
        if user:
            user.login_attempts = (user.login_attempts or 0) + 1
            log_action = "USER_LOGIN_FAILED"
            if user.login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = _utcnow() + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
                user.login_attempts = 0
                log_action = "ACCOUNT_LOCKED"
                await mon.record_security_event(
                    db, event_type="multiple_failed_logins", severity="high",
                    user_id=user.id, ip_address=client_ip,
                    device_id=mon.device_id_from_request(request),
                )
            db.add(user)
            await record_audit(
                db, action=log_action, user_id=user.id, resource_type="user",
                resource_id=user.id, description="Failed login attempt",
                ip_address=client_ip, user_agent=request.headers.get("user-agent"),
                status="failure", username=user.email,
                user_role=user.role.value if user.role else None,
                device_id=mon.device_id_from_request(request),
            )
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is disabled")

    # Second factor (TOTP or a one-time backup code) when MFA is enabled.
    if user.mfa_enabled and user.mfa_secret:
        code = (credentials.mfa_code or "").strip()
        if not code:
            raise HTTPException(status_code=401, detail="MFA code required")
        ok = pyotp.TOTP(user.mfa_secret).verify(code, valid_window=1)
        if not ok:
            remaining = list(user.mfa_backup_codes or [])
            used = next((h for h in remaining if verify_password(code, h)), None)
            if used:
                remaining.remove(used)
                user.mfa_backup_codes = remaining
                ok = True
        if not ok:
            await record_audit(
                db, action="MFA_FAILED", user_id=user.id, resource_type="user",
                resource_id=user.id, description="Invalid MFA code", ip_address=client_ip,
                status="failure",
            )
            await db.commit()
            raise HTTPException(status_code=401, detail="Invalid MFA code")

    user.login_attempts = 0
    user.locked_until = None
    user.last_login = _utcnow()
    db.add(user)

    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    jti = (decode_token(access) or {}).get("jti")

    # Device intelligence, session, IP/login history + security events
    await mon.process_successful_login(db, user, request, jti)

    await record_audit(
        db, action="USER_LOGIN", user_id=user.id, resource_type="user",
        resource_id=user.id, description="User logged in",
        ip_address=client_ip, user_agent=request.headers.get("user-agent"),
        username=user.email, user_role=user.role.value if user.role else None,
        device_id=mon.device_id_from_request(request),
    )
    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh")
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    # Token is taken from the request body (never the URL/query string, which
    # would leak into logs and browser history). Must be a refresh-type token.
    user_id = verify_token(body.refresh_token, expected_type="refresh")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in updates.model_dump(exclude_none=True).items():
        if field == "role":
            continue  # self-role change not allowed
        setattr(current_user, field, value)
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the presented access token so it can no longer be used."""
    payload = decode_token(credentials.credentials)
    if payload and payload.get("jti"):
        exp = payload.get("exp")
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else _utcnow()
        db.add(RevokedToken(jti=payload["jti"], user_id=current_user.id, expires_at=expires_at))
        await mon.close_session_by_jti(db, payload["jti"])
        await record_audit(
            db, action="USER_LOGOUT", user_id=current_user.id, resource_type="user",
            resource_id=current_user.id, description="User logged out",
            username=current_user.email,
            user_role=current_user.role.value if current_user.role else None,
        )
        await db.commit()
    return {"message": "Logged out"}


# --------------------------------------------------------------------------
# Multi-factor authentication (TOTP)
# --------------------------------------------------------------------------
@router.post("/mfa/setup")
async def mfa_setup(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a TOTP secret and provisioning URI. MFA is not active until verified."""
    secret = pyotp.random_base32()
    current_user.mfa_secret = secret
    current_user.mfa_enabled = False
    db.add(current_user)
    await db.commit()
    uri = pyotp.TOTP(secret).provisioning_uri(name=current_user.email, issuer_name=MFA_ISSUER)
    return {"secret": secret, "otpauth_uri": uri}


@router.post("/mfa/verify")
async def mfa_verify(
    body: MFAVerify,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm the first TOTP code, activate MFA, and issue one-time backup codes."""
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="Run MFA setup first")
    if not pyotp.TOTP(current_user.mfa_secret).verify(body.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid code")

    plain_codes = _gen_backup_codes()
    current_user.mfa_enabled = True
    current_user.mfa_backup_codes = [get_password_hash(c) for c in plain_codes]
    db.add(current_user)
    await record_audit(
        db, action="MFA_ENABLED", user_id=current_user.id, resource_type="user",
        resource_id=current_user.id, description="MFA enabled",
    )
    await db.commit()
    # Backup codes are shown only once.
    return {"enabled": True, "backup_codes": plain_codes}


@router.post("/mfa/disable")
async def mfa_disable(
    body: MFAVerify,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable MFA (requires a valid current TOTP code)."""
    if current_user.mfa_enabled and current_user.mfa_secret:
        if not pyotp.TOTP(current_user.mfa_secret).verify(body.code, valid_window=1):
            raise HTTPException(status_code=400, detail="Invalid code")
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    current_user.mfa_backup_codes = None
    db.add(current_user)
    await record_audit(
        db, action="MFA_DISABLED", user_id=current_user.id, resource_type="user",
        resource_id=current_user.id, description="MFA disabled",
    )
    await db.commit()
    return {"enabled": False}


# --------------------------------------------------------------------------
# Password reset
# --------------------------------------------------------------------------
@router.post("/password-reset/request")
@limiter.limit("5/minute")
async def password_reset_request(
    body: PasswordReset, request: Request, db: AsyncSession = Depends(get_db),
):
    """Issue a single-use reset token. Does not reveal whether the email exists."""
    user = (
        await db.execute(select(User).where(User.email == body.email))
    ).scalar_one_or_none()
    token_plain = _secrets.token_urlsafe(32)
    if user:
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=hashlib.sha256(token_plain.encode()).hexdigest(),
            expires_at=_utcnow() + timedelta(hours=1),
        ))
        await record_audit(
            db, action="PASSWORD_RESET_REQUESTED", user_id=user.id, resource_type="user",
            resource_id=user.id, description="Password reset requested",
            ip_address=request.client.host if request.client else None,
        )
        await db.commit()

    resp = {"message": "If that email exists, a reset link has been sent"}
    # In non-production, surface the token so the flow can be exercised without email.
    if user and settings.ENVIRONMENT.lower() != "production":
        resp["debug_token"] = token_plain
    return resp


@router.post("/password-reset/confirm")
async def password_reset_confirm(
    body: PasswordResetConfirm, db: AsyncSession = Depends(get_db),
):
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    prt = (
        await db.execute(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    ).scalar_one_or_none()
    if not prt or prt.used_at is not None or _as_aware(prt.expires_at) < _utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = (await db.execute(select(User).where(User.id == prt.user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user.hashed_password = get_password_hash(body.new_password)
    user.login_attempts = 0
    user.locked_until = None
    prt.used_at = _utcnow()
    db.add(user)
    db.add(prt)
    await record_audit(
        db, action="PASSWORD_RESET_COMPLETED", user_id=user.id, resource_type="user",
        resource_id=user.id, description="Password reset completed",
    )
    await db.commit()
    return {"message": "Password updated"}
