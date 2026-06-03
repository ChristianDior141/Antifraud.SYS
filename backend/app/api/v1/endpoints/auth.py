from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    verify_password, get_password_hash, create_access_token, create_refresh_token, verify_token
)
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.services.audit_service import record_audit
from app.schemas.user import (
    UserCreate, UserLogin, TokenResponse, UserResponse, UserUpdate, RefreshRequest,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime) -> datetime:
    """Normalise a possibly-naive datetime (e.g. from SQLite) to UTC-aware."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
    )
    db.add(user)
    await db.flush()

    await record_audit(
        db, action="USER_REGISTERED", user_id=user.id, resource_type="user",
        resource_id=user.id, description=f"New user registered: {user.email}",
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
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
        if user:
            user.login_attempts = (user.login_attempts or 0) + 1
            log_action = "USER_LOGIN_FAILED"
            if user.login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = _utcnow() + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
                user.login_attempts = 0
                log_action = "ACCOUNT_LOCKED"
            db.add(user)
            await record_audit(
                db, action=log_action, user_id=user.id, resource_type="user",
                resource_id=user.id, description="Failed login attempt",
                ip_address=client_ip, user_agent=request.headers.get("user-agent"),
                status="failure",
            )
            await db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is disabled")

    user.login_attempts = 0
    user.locked_until = None
    user.last_login = _utcnow()
    db.add(user)

    await record_audit(
        db, action="USER_LOGIN", user_id=user.id, resource_type="user",
        resource_id=user.id, description="User logged in",
        ip_address=client_ip, user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
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
