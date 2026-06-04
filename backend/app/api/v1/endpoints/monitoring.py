import csv
import io
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.models.audit import AuditLog
from app.models.monitoring import (
    Device, UserSession, LoginHistory, IPHistory, UserActivityLog, SecurityEvent,
)
from app.schemas.monitoring import (
    DeviceResponse, SessionResponse, LoginHistoryResponse, SecurityEventResponse,
    ActivityLogResponse,
)

router = APIRouter(prefix="/monitoring", tags=["Monitoring & Audit"])


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


# ==========================================================================
# Self-service — any authenticated user, OWN data only
# ==========================================================================
@router.get("/me/devices", response_model=List[DeviceResponse])
async def my_devices(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Device).where(Device.user_id == current_user.id).order_by(Device.last_seen.desc()))
    return res.scalars().all()


@router.get("/me/login-history", response_model=List[LoginHistoryResponse])
async def my_login_history(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(LoginHistory).where(LoginHistory.user_id == current_user.id)
        .order_by(LoginHistory.id.desc()).limit(100)
    )
    return res.scalars().all()


@router.get("/me/sessions", response_model=List[SessionResponse])
async def my_sessions(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(UserSession).where(UserSession.user_id == current_user.id)
        .order_by(UserSession.id.desc()).limit(100)
    )
    return res.scalars().all()


@router.get("/me/activity", response_model=List[ActivityLogResponse])
async def my_activity(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(UserActivityLog).where(UserActivityLog.user_id == current_user.id)
        .order_by(UserActivityLog.id.desc()).limit(200)
    )
    return res.scalars().all()


@router.post("/devices/{device_id}/trust", response_model=DeviceResponse)
async def trust_device(device_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    dev = (await db.execute(select(Device).where(Device.id == device_id))).scalar_one_or_none()
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    # Only the owner (or an admin) may mark a device trusted.
    if dev.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not your device")
    dev.is_trusted = True
    db.add(dev)
    await db.commit()
    await db.refresh(dev)
    return dev


# ==========================================================================
# Administrator audit dashboard — admin only
# ==========================================================================
@router.get("/audit")
async def admin_audit(
    q: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if q:
        query = query.where(or_(
            AuditLog.username.ilike(f"%{q}%"),
            AuditLog.description.ilike(f"%{q}%"),
            AuditLog.ip_address.ilike(f"%{q}%"),
        ))
    df, dt = _parse_dt(date_from), _parse_dt(date_to)
    if df:
        query = query.where(AuditLog.created_at >= df)
    if dt:
        query = query.where(AuditLog.created_at <= dt)
    query = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()
    return [
        {
            "id": r.id, "user_id": r.user_id, "username": r.username, "role": r.user_role,
            "action": r.action, "entity_type": r.resource_type, "entity_id": r.resource_id,
            "ip_address": r.ip_address, "device_id": r.device_id, "result": r.status,
            "details": r.description,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/activity", response_model=List[ActivityLogResponse])
async def admin_activity(
    user_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(UserActivityLog)
    if user_id:
        query = query.where(UserActivityLog.user_id == user_id)
    query = query.order_by(UserActivityLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return (await db.execute(query)).scalars().all()


@router.get("/devices", response_model=List[DeviceResponse])
async def admin_devices(current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(Device).order_by(Device.last_seen.desc()).limit(500))).scalars().all()


@router.get("/sessions", response_model=List[SessionResponse])
async def admin_sessions(
    active_only: bool = False,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(UserSession)
    if active_only:
        query = query.where(UserSession.is_active == True)  # noqa: E712
    return (await db.execute(query.order_by(UserSession.id.desc()).limit(500))).scalars().all()


@router.get("/login-history", response_model=List[LoginHistoryResponse])
async def admin_login_history(
    failed_only: bool = False,
    user_id: Optional[int] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(LoginHistory)
    if failed_only:
        query = query.where(LoginHistory.success == False)  # noqa: E712
    if user_id:
        query = query.where(LoginHistory.user_id == user_id)
    return (await db.execute(query.order_by(LoginHistory.id.desc()).limit(500))).scalars().all()


@router.get("/security-events", response_model=List[SecurityEventResponse])
async def admin_security_events(
    severity: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(SecurityEvent)
    if severity:
        query = query.where(SecurityEvent.severity == severity)
    return (await db.execute(query.order_by(SecurityEvent.id.desc()).limit(500))).scalars().all()


@router.get("/users/{target_id}/activity")
async def user_activity_timeline(
    target_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Consolidated activity timeline for one user (audit + business activity)."""
    audit = (await db.execute(
        select(AuditLog).where(AuditLog.user_id == target_id).order_by(AuditLog.id.desc()).limit(200)
    )).scalars().all()
    activity = (await db.execute(
        select(UserActivityLog).where(UserActivityLog.user_id == target_id).order_by(UserActivityLog.id.desc()).limit(200)
    )).scalars().all()
    timeline = (
        [{"source": "audit", "action": a.action, "entity_type": a.resource_type,
          "entity_id": a.resource_id, "ip": a.ip_address, "device_id": a.device_id,
          "result": a.status, "at": a.created_at.isoformat() if a.created_at else None}
         for a in audit]
        + [{"source": "activity", "action": x.action_type, "entity_type": x.entity_type,
            "entity_id": x.entity_id, "ip": x.ip_address, "device_id": x.device_id,
            "result": x.result, "at": x.created_at.isoformat() if x.created_at else None}
           for x in activity]
    )
    timeline.sort(key=lambda r: r["at"] or "", reverse=True)
    return {"user_id": target_id, "events": timeline}


# ==========================================================================
# Export — admin only (CSV / Excel / PDF)
# ==========================================================================
async def _dataset_rows(dataset: str, db: AsyncSession):
    if dataset == "audit":
        rows = (await db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(5000))).scalars().all()
        headers = ["id", "username", "role", "action", "entity_type", "entity_id", "ip_address", "device_id", "result", "created_at"]
        data = [[r.id, r.username, r.user_role, r.action, r.resource_type, r.resource_id,
                 r.ip_address, r.device_id, r.status,
                 r.created_at.isoformat() if r.created_at else ""] for r in rows]
    elif dataset == "activity":
        rows = (await db.execute(select(UserActivityLog).order_by(UserActivityLog.id.desc()).limit(5000))).scalars().all()
        headers = ["id", "username", "role", "action_type", "entity_type", "entity_id", "ip_address", "device_id", "result", "created_at"]
        data = [[r.id, r.username, r.role, r.action_type, r.entity_type, r.entity_id,
                 r.ip_address, r.device_id, r.result,
                 r.created_at.isoformat() if r.created_at else ""] for r in rows]
    elif dataset == "login-history":
        rows = (await db.execute(select(LoginHistory).order_by(LoginHistory.id.desc()).limit(5000))).scalars().all()
        headers = ["id", "email", "ip_address", "device_id", "success", "created_at"]
        data = [[r.id, r.email, r.ip_address, r.device_id, r.success,
                 r.created_at.isoformat() if r.created_at else ""] for r in rows]
    elif dataset == "security-events":
        rows = (await db.execute(select(SecurityEvent).order_by(SecurityEvent.id.desc()).limit(5000))).scalars().all()
        headers = ["id", "event_type", "severity", "user_id", "ip_address", "device_id", "resolved", "created_at"]
        data = [[r.id, r.event_type, r.severity, r.user_id, r.ip_address, r.device_id, r.resolved,
                 r.created_at.isoformat() if r.created_at else ""] for r in rows]
    else:
        raise HTTPException(status_code=400, detail="Unknown dataset")
    return headers, data


@router.get("/export")
async def export_logs(
    dataset: str = Query("audit"),
    format: str = Query("csv", pattern="^(csv|xlsx|pdf)$"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    headers, data = await _dataset_rows(dataset, db)
    filename = f"{dataset}-{datetime.utcnow().strftime('%Y%m%d')}"

    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(headers)
        writer.writerows(data)
        return StreamingResponse(
            iter([buf.getvalue()]), media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
        )

    if format == "xlsx":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = dataset[:31]
        ws.append(headers)
        for row in data:
            ws.append([("" if c is None else c) for c in row])
        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        return Response(
            content=out.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}.xlsx"'},
        )

    # PDF
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=landscape(A4))
    table_data = [headers] + [[("" if c is None else str(c)) for c in row] for row in data[:500]]
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
    ]))
    doc.build([table])
    out.seek(0)
    return Response(
        content=out.getvalue(), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
    )
