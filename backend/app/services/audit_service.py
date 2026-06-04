"""Tamper-evident audit logging (ISO 27001 A.12.4.1 / A.12.4.2).

All audit entries are written through ``record_audit`` so they form an
append-only hash chain: ``entry_hash = SHA256(prev_hash | payload)``. Any later
edit or deletion of a record breaks every subsequent link, which
``verify_audit_chain`` detects.
"""
from datetime import datetime, timezone
from hashlib import sha256
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

GENESIS = "GENESIS"


def _ts(dt: datetime) -> str:
    """Deterministic UTC timestamp string (stable across naive/aware reads)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")


def _payload(prev_hash: str, *, user_id, action, resource_type, resource_id,
             description, status, created_at) -> str:
    return "|".join([
        prev_hash,
        str(user_id), str(action), str(resource_type or ""), str(resource_id or ""),
        str(description or ""), str(status or ""), _ts(created_at),
    ])


async def record_audit(
    db: AsyncSession,
    *,
    action: str,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    description: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "success",
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
    username: Optional[str] = None,
    user_role: Optional[str] = None,
    device_id: Optional[str] = None,
) -> AuditLog:
    """Append a hash-chained audit entry. Flushes so consecutive calls chain correctly."""
    last = (
        await db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
    ).scalar_one_or_none()
    prev_hash = last.entry_hash if last and last.entry_hash else GENESIS

    created_at = datetime.now(timezone.utc)
    entry_hash = sha256(
        _payload(
            prev_hash, user_id=user_id, action=action, resource_type=resource_type,
            resource_id=resource_id, description=description, status=status,
            created_at=created_at,
        ).encode()
    ).hexdigest()

    log = AuditLog(
        user_id=user_id, action=action, resource_type=resource_type,
        resource_id=resource_id, description=description, ip_address=ip_address,
        user_agent=user_agent, status=status, old_values=old_values,
        new_values=new_values, username=username, user_role=user_role,
        device_id=device_id, prev_hash=prev_hash, entry_hash=entry_hash,
        created_at=created_at,
    )
    db.add(log)
    await db.flush()
    return log


async def log_pii_access(
    db: AsyncSession, *, user_id: int, resource_type: str, resource_id: int,
    description: Optional[str] = None, ip_address: Optional[str] = None,
) -> AuditLog:
    """Convenience wrapper to record that a staff member viewed personal data."""
    return await record_audit(
        db, action="PII_VIEWED", user_id=user_id, resource_type=resource_type,
        resource_id=resource_id,
        description=description or f"Viewed {resource_type} #{resource_id}",
        ip_address=ip_address,
    )


async def verify_audit_chain(db: AsyncSession) -> dict:
    """Recompute the chain and report the first broken link (if any)."""
    rows = (await db.execute(select(AuditLog).order_by(AuditLog.id.asc()))).scalars().all()
    prev_hash = GENESIS
    for row in rows:
        expected = sha256(
            _payload(
                prev_hash, user_id=row.user_id, action=row.action,
                resource_type=row.resource_type, resource_id=row.resource_id,
                description=row.description, status=row.status, created_at=row.created_at,
            ).encode()
        ).hexdigest()
        if row.prev_hash != prev_hash or row.entry_hash != expected:
            return {"valid": False, "total": len(rows), "broken_at_id": row.id}
        prev_hash = row.entry_hash
    return {"valid": True, "total": len(rows), "broken_at_id": None}
