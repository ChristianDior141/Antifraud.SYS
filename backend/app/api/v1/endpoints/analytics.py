from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from app.core.database import get_db
from app.core.deps import require_analyst
from app.models.user import User
from app.models.client import ClientProfile, KYCStatus, RiskLevel
from app.models.aml import AMLAlert, AlertSeverity, AlertStatus
from app.models.transaction import Transaction
from app.models.document import Document
from app.models.detection_rule import DetectionRule
from app.models.incident import (
    IncidentTicket, FalsePositive, TicketStatus, IncidentClassification,
)
from datetime import datetime, timedelta

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _months_back(n: int = 6):
    """Yield (label, start, end) for the last `n` calendar-ish months."""
    out = []
    for i in range(n - 1, -1, -1):
        start = datetime.utcnow().replace(day=1) - timedelta(days=i * 30)
        end = start + timedelta(days=30)
        out.append((start.strftime("%b %Y"), start, end))
    return out


@router.get("/dashboard")
async def dashboard_stats(
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    # Client stats
    total_clients = await db.execute(select(func.count(ClientProfile.id)))
    approved = await db.execute(
        select(func.count(ClientProfile.id)).where(ClientProfile.kyc_status == KYCStatus.APPROVED)
    )
    rejected = await db.execute(
        select(func.count(ClientProfile.id)).where(ClientProfile.kyc_status == KYCStatus.REJECTED)
    )
    pending = await db.execute(
        select(func.count(ClientProfile.id)).where(ClientProfile.kyc_status == KYCStatus.PENDING_REVIEW)
    )

    # Risk distribution
    low_risk = await db.execute(
        select(func.count(ClientProfile.id)).where(ClientProfile.risk_level == RiskLevel.LOW)
    )
    medium_risk = await db.execute(
        select(func.count(ClientProfile.id)).where(ClientProfile.risk_level == RiskLevel.MEDIUM)
    )
    high_risk = await db.execute(
        select(func.count(ClientProfile.id)).where(ClientProfile.risk_level == RiskLevel.HIGH)
    )
    critical_risk = await db.execute(
        select(func.count(ClientProfile.id)).where(ClientProfile.risk_level == RiskLevel.CRITICAL)
    )

    # AML stats
    open_alerts = await db.execute(
        select(func.count(AMLAlert.id)).where(AMLAlert.status == AlertStatus.OPEN)
    )
    critical_alerts = await db.execute(
        select(func.count(AMLAlert.id)).where(AMLAlert.severity == AlertSeverity.CRITICAL)
    )

    # Transaction stats
    total_txns = await db.execute(select(func.count(Transaction.id)))
    flagged_txns = await db.execute(
        select(func.count(Transaction.id)).where(Transaction.is_flagged == True)
    )
    total_volume = await db.execute(select(func.sum(Transaction.amount)))

    # Documents pending
    docs_pending = await db.execute(
        select(func.count(Document.id)).where(Document.status == "pending")
    )

    tc = total_clients.scalar() or 0
    ap = approved.scalar() or 0

    return {
        "clients": {
            "total": tc,
            "approved": ap,
            "rejected": rejected.scalar() or 0,
            "pending_review": pending.scalar() or 0,
            "approval_rate": round((ap / tc * 100) if tc > 0 else 0, 1),
        },
        "risk_distribution": {
            "low": low_risk.scalar() or 0,
            "medium": medium_risk.scalar() or 0,
            "high": high_risk.scalar() or 0,
            "critical": critical_risk.scalar() or 0,
        },
        "aml": {
            "open_alerts": open_alerts.scalar() or 0,
            "critical_alerts": critical_alerts.scalar() or 0,
        },
        "transactions": {
            "total": total_txns.scalar() or 0,
            "flagged": flagged_txns.scalar() or 0,
            "total_volume": float(total_volume.scalar() or 0),
        },
        "documents_pending_review": docs_pending.scalar() or 0,
    }


@router.get("/monthly-trend")
async def monthly_trend(
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    months = []
    for i in range(5, -1, -1):
        start = datetime.utcnow().replace(day=1) - timedelta(days=i * 30)
        end = start + timedelta(days=30)
        label = start.strftime("%b %Y")

        clients_count = await db.execute(
            select(func.count(ClientProfile.id)).where(
                ClientProfile.created_at >= start, ClientProfile.created_at < end
            )
        )
        alerts_count = await db.execute(
            select(func.count(AMLAlert.id)).where(
                AMLAlert.created_at >= start, AMLAlert.created_at < end
            )
        )
        months.append({
            "month": label,
            "new_clients": clients_count.scalar() or 0,
            "aml_alerts": alerts_count.scalar() or 0,
        })
    return months


# --------------------------------------------------------------------------
# Incident Management & False Positive analytics
# --------------------------------------------------------------------------

def _mean_hours(deltas) -> float:
    vals = [d.total_seconds() / 3600 for d in deltas if d is not None]
    return round(sum(vals) / len(vals), 1) if vals else 0.0


@router.get("/incidents")
async def incident_metrics(
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(IncidentTicket))
    tickets = result.scalars().all()

    total = len(tickets)
    closed = [t for t in tickets if t.status == TicketStatus.CLOSED]
    open_tickets = total - len(closed)

    # MTTR: created -> closed ; MTTA: created -> first assigned
    resolution_deltas = [
        (t.closed_at.replace(tzinfo=None) - t.created_at.replace(tzinfo=None))
        for t in tickets if t.closed_at and t.created_at
    ]
    ack_deltas = [
        (t.first_assigned_at.replace(tzinfo=None) - t.created_at.replace(tzinfo=None))
        for t in tickets if t.first_assigned_at and t.created_at
    ]
    mttr = _mean_hours(resolution_deltas)
    mtta = _mean_hours(ack_deltas)

    return {
        "total_incidents": total,
        "open_incidents": open_tickets,
        "closed_incidents": len(closed),
        "average_resolution_hours": mttr,
        "mttr_hours": mttr,
        "mtta_hours": mtta,
        "by_status": {
            s.value: sum(1 for t in tickets if t.status == s) for s in TicketStatus
        },
    }


@router.get("/false-positives")
async def false_positive_metrics(
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    tickets = (await db.execute(select(IncidentTicket))).scalars().all()
    fps = (await db.execute(select(FalsePositive))).scalars().all()
    rules = (await db.execute(select(DetectionRule))).scalars().all()
    rule_name = {r.id: r.name for r in rules}

    classified = [t for t in tickets if t.classification is not None]
    total_fp = sum(1 for t in classified if t.classification == IncidentClassification.FALSE_POSITIVE)
    fp_rate = round(total_fp / len(classified) * 100, 1) if classified else 0.0

    by_rule = {}
    for f in fps:
        key = rule_name.get(f.detection_rule_id, "Unknown")
        by_rule[key] = by_rule.get(key, 0) + 1

    by_source = {}
    for f in fps:
        key = f.source_system or "Unknown"
        by_source[key] = by_source.get(key, 0) + 1

    # Monthly trend of FP rate (classified tickets bucketed by creation month)
    trend = []
    for label, start, end in _months_back(6):
        bucket = [
            t for t in classified
            if t.created_at and start <= t.created_at.replace(tzinfo=None) < end
        ]
        bfp = sum(1 for t in bucket if t.classification == IncidentClassification.FALSE_POSITIVE)
        rate = round(bfp / len(bucket) * 100, 1) if bucket else 0.0
        trend.append({
            "month": label,
            "false_positives": bfp,
            "classified": len(bucket),
            "false_positive_rate": rate,
        })

    return {
        "total_false_positives": total_fp,
        "false_positive_rate": fp_rate,
        "by_rule": by_rule,
        "by_source": by_source,
        "monthly_trend": trend,
    }


@router.get("/risk")
async def risk_metrics(
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    from app.models.client import RiskLevel
    tickets = (await db.execute(select(IncidentTicket))).scalars().all()
    return {
        "low": sum(1 for t in tickets if t.risk_level == RiskLevel.LOW),
        "medium": sum(1 for t in tickets if t.risk_level == RiskLevel.MEDIUM),
        "high": sum(1 for t in tickets if t.risk_level == RiskLevel.HIGH),
        "critical": sum(1 for t in tickets if t.risk_level == RiskLevel.CRITICAL),
    }
