"""Device intelligence, session/IP/login tracking and security-event detection."""
import hashlib
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.monitoring import (
    Device, UserSession, LoginHistory, IPHistory, UserActivityLog, SecurityEvent,
)

RAPID_IP_WINDOW = timedelta(minutes=10)


# --------------------------------------------------------------------------
# Request metadata helpers
# --------------------------------------------------------------------------
def client_ip(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def parse_user_agent(ua: str) -> dict:
    """Lightweight UA parsing (no external dependency)."""
    ua = ua or ""
    u = ua.lower()
    # OS
    if "windows" in u:
        os_name = "Windows"
    elif "android" in u:
        os_name = "Android"
    elif "iphone" in u or "ipad" in u or "ios" in u:
        os_name = "iOS"
    elif "mac os" in u or "macintosh" in u:
        os_name = "macOS"
    elif "linux" in u:
        os_name = "Linux"
    else:
        os_name = "Unknown"
    # Browser (order matters: Edge/Chrome/Safari)
    if "edg" in u:
        browser = "Edge"
    elif "chrome" in u or "crios" in u:
        browser = "Chrome"
    elif "firefox" in u:
        browser = "Firefox"
    elif "safari" in u:
        browser = "Safari"
    else:
        browser = "Unknown"
    # Device type
    if "mobile" in u or "iphone" in u or "android" in u:
        device_type = "mobile"
    elif "tablet" in u or "ipad" in u:
        device_type = "tablet"
    else:
        device_type = "desktop"
    return {
        "operating_system": os_name,
        "browser": browser,
        "device_type": device_type,
        "device_name": f"{browser} on {os_name}",
    }


def device_id_from_request(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    did = request.headers.get("x-device-id")
    if did:
        return did[:128]
    # Fallback: derive a stable id from UA + IP so a device is still trackable.
    ua = request.headers.get("user-agent", "")
    ip = client_ip(request) or ""
    return "ua-" + hashlib.sha256(f"{ua}|{ip}".encode()).hexdigest()[:24]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt):
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# --------------------------------------------------------------------------
# Writers
# --------------------------------------------------------------------------
async def upsert_device(
    db: AsyncSession, user_id: int, request: Request,
    screen_resolution: Optional[str] = None,
) -> Tuple[Optional[Device], bool]:
    did = device_id_from_request(request)
    if not did or user_id is None:
        return None, False
    ua = request.headers.get("user-agent", "")
    info = parse_user_agent(ua)

    existing = (
        await db.execute(
            select(Device).where(Device.user_id == user_id, Device.device_id == did)
        )
    ).scalar_one_or_none()

    is_new = existing is None
    if existing:
        existing.last_seen = _utcnow()
        if screen_resolution:
            existing.screen_resolution = screen_resolution
        db.add(existing)
        device = existing
    else:
        device = Device(
            user_id=user_id, device_id=did, user_agent=ua[:1000],
            screen_resolution=screen_resolution, **info,
        )
        db.add(device)
    await db.flush()
    return device, is_new


async def record_security_event(
    db: AsyncSession, *, event_type: str, severity: str = "medium",
    user_id: Optional[int] = None, ip_address: Optional[str] = None,
    device_id: Optional[str] = None, metadata: Optional[dict] = None,
) -> SecurityEvent:
    evt = SecurityEvent(
        event_type=event_type, severity=severity, user_id=user_id,
        ip_address=ip_address, device_id=device_id, event_metadata=metadata,
    )
    db.add(evt)
    await db.flush()
    return evt


async def record_activity(
    db: AsyncSession, *, user: User, action_type: str,
    entity_type: Optional[str] = None, entity_id: Optional[int] = None,
    request: Optional[Request] = None, result: str = "success",
    details: Optional[str] = None,
) -> UserActivityLog:
    log = UserActivityLog(
        user_id=user.id, username=user.email,
        role=user.role.value if user.role else None,
        action_type=action_type, entity_type=entity_type, entity_id=entity_id,
        ip_address=client_ip(request), device_id=device_id_from_request(request),
        result=result, details=details,
    )
    db.add(log)
    await db.flush()
    return log


async def record_failed_login(
    db: AsyncSession, email: str, request: Request, user_id: Optional[int] = None,
) -> None:
    db.add(LoginHistory(
        user_id=user_id, email=email, ip_address=client_ip(request),
        device_id=device_id_from_request(request),
        user_agent=request.headers.get("user-agent", "")[:1000], success=False,
    ))
    await db.flush()


async def process_successful_login(
    db: AsyncSession, user: User, request: Request, jti: Optional[str],
    screen_resolution: Optional[str] = None,
) -> List[str]:
    """Record device/session/IP/login history and emit security events.
    Returns the list of security-event types triggered."""
    ip = client_ip(request)
    ua = request.headers.get("user-agent", "")
    did = device_id_from_request(request)
    events: List[str] = []

    # Look at the previous successful login BEFORE inserting the current one.
    prev = (
        await db.execute(
            select(LoginHistory)
            .where(LoginHistory.user_id == user.id, LoginHistory.success == True)  # noqa: E712
            .order_by(LoginHistory.id.desc()).limit(1)
        )
    ).scalar_one_or_none()

    # Login history (success)
    db.add(LoginHistory(
        user_id=user.id, email=user.email, ip_address=ip, device_id=did,
        user_agent=ua[:1000], success=True,
    ))

    # Device
    device, is_new_device = await upsert_device(db, user.id, request, screen_resolution)
    if is_new_device and (device is None or not device.is_trusted):
        events.append("new_device")
        await record_security_event(
            db, event_type="new_device", severity="medium", user_id=user.id,
            ip_address=ip, device_id=did, metadata={"user_agent": ua[:200]},
        )

    # IP history / new IP
    ip_row = None
    if ip:
        ip_row = (
            await db.execute(
                select(IPHistory).where(IPHistory.user_id == user.id, IPHistory.ip_address == ip)
            )
        ).scalar_one_or_none()
        if ip_row:
            ip_row.last_seen = _utcnow()
            db.add(ip_row)
        else:
            db.add(IPHistory(user_id=user.id, ip_address=ip))
            events.append("new_ip")
            await record_security_event(
                db, event_type="new_ip", severity="medium", user_id=user.id,
                ip_address=ip, device_id=did,
            )

    # Rapid IP change
    if prev and prev.ip_address and ip and prev.ip_address != ip:
        if _aware(prev.created_at) and (_utcnow() - _aware(prev.created_at)) < RAPID_IP_WINDOW:
            events.append("rapid_ip_change")
            await record_security_event(
                db, event_type="rapid_ip_change", severity="high", user_id=user.id,
                ip_address=ip, device_id=did,
                metadata={"previous_ip": prev.ip_address, "current_ip": ip},
            )

    # Session
    db.add(UserSession(
        user_id=user.id, token_jti=jti, device_id=did, ip_address=ip,
        user_agent=ua[:1000],
    ))
    await db.flush()
    return events


async def close_session_by_jti(db: AsyncSession, jti: Optional[str]) -> None:
    if not jti:
        return
    sess = (
        await db.execute(select(UserSession).where(UserSession.token_jti == jti))
    ).scalar_one_or_none()
    if sess and sess.is_active:
        sess.is_active = False
        sess.logout_at = _utcnow()
        db.add(sess)
        await db.flush()
