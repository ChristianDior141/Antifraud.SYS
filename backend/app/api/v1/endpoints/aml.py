from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from app.core.database import get_db
from app.core.deps import require_compliance, require_analyst
from app.models.user import User
from app.models.aml import AMLAlert, AlertStatus, AlertSeverity
from app.schemas.aml import AMLAlertResponse, AMLAlertUpdate

router = APIRouter(prefix="/aml", tags=["AML Monitoring"])


@router.get("/alerts", response_model=List[AMLAlertResponse])
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[AlertStatus] = None,
    severity: Optional[AlertSeverity] = None,
    client_id: Optional[int] = None,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    query = select(AMLAlert)
    if status:
        query = query.where(AMLAlert.status == status)
    if severity:
        query = query.where(AMLAlert.severity == severity)
    if client_id:
        query = query.where(AMLAlert.client_id == client_id)
    query = query.order_by(AMLAlert.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/alerts/{alert_id}", response_model=AMLAlertResponse)
async def get_alert(
    alert_id: int,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AMLAlert).where(AMLAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.put("/alerts/{alert_id}", response_model=AMLAlertResponse)
async def update_alert(
    alert_id: int,
    updates: AMLAlertUpdate,
    current_user: User = Depends(require_compliance),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AMLAlert).where(AMLAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    from datetime import datetime
    for field, value in updates.model_dump(exclude_none=True).items():
        setattr(alert, field, value)

    if updates.status in [AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE, AlertStatus.SAR_FILED]:
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = current_user.id

    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.get("/stats")
async def aml_stats(
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    total = await db.execute(select(func.count(AMLAlert.id)))
    open_alerts = await db.execute(
        select(func.count(AMLAlert.id)).where(AMLAlert.status == AlertStatus.OPEN)
    )
    critical = await db.execute(
        select(func.count(AMLAlert.id)).where(AMLAlert.severity == AlertSeverity.CRITICAL)
    )
    return {
        "total_alerts": total.scalar() or 0,
        "open_alerts": open_alerts.scalar() or 0,
        "critical_alerts": critical.scalar() or 0,
    }
