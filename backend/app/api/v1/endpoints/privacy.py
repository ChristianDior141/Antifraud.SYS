from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.models.privacy import DataSubjectRequest, Consent, DSARType, DSARStatus
from app.schemas.privacy import (
    DSARCreate, DSARProcess, DSARResponse, ConsentUpsert, ConsentResponse,
)
from app.services.audit_service import record_audit, verify_audit_chain
from app.services.privacy_service import (
    export_subject_data, anonymize_user, purge_expired_data,
)

router = APIRouter(prefix="/privacy", tags=["Privacy & GDPR"])

DSAR_SLA_DAYS = 30


def _client_ip(request: Request):
    return request.client.host if request.client else None


# --------------------------------------------------------------------------
# Data subject self-service
# --------------------------------------------------------------------------
@router.get("/my-data/export")
async def export_my_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Right of access / portability (GDPR Art.15 & 20)."""
    data = await export_subject_data(db, current_user)
    await record_audit(
        db, action="PII_EXPORTED", user_id=current_user.id,
        resource_type="user", resource_id=current_user.id,
        description="Data subject exported their personal data",
        ip_address=_client_ip(request),
    )
    await db.commit()
    return data


@router.get("/consents", response_model=List[ConsentResponse])
async def list_my_consents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Consent).where(Consent.user_id == current_user.id))
    return result.scalars().all()


@router.post("/consents", response_model=ConsentResponse)
async def upsert_consent(
    body: ConsentUpsert,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Grant or withdraw consent for a purpose (GDPR Art.7)."""
    now = datetime.now(timezone.utc)
    existing = (
        await db.execute(
            select(Consent).where(
                Consent.user_id == current_user.id, Consent.purpose == body.purpose
            ).order_by(Consent.id.desc()).limit(1)
        )
    ).scalar_one_or_none()

    consent = existing or Consent(user_id=current_user.id, purpose=body.purpose)
    consent.policy_version = body.policy_version
    consent.granted = body.granted
    consent.ip_address = _client_ip(request)
    if body.granted:
        consent.granted_at = now
        consent.revoked_at = None
    else:
        consent.revoked_at = now
    db.add(consent)

    await record_audit(
        db, action="CONSENT_UPDATED", user_id=current_user.id,
        resource_type="consent", resource_id=None,
        description=f"Consent '{body.purpose}' set to granted={body.granted}",
        ip_address=_client_ip(request),
    )
    await db.commit()
    await db.refresh(consent)
    return consent


@router.post("/requests", response_model=DSARResponse, status_code=201)
async def create_dsar(
    body: DSARCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a data-subject request (access/export/erasure/restriction/rectification)."""
    dsar = DataSubjectRequest(
        user_id=current_user.id,
        request_type=body.request_type,
        details=body.details,
        status=DSARStatus.RECEIVED,
        due_at=datetime.now(timezone.utc) + timedelta(days=DSAR_SLA_DAYS),
    )
    db.add(dsar)
    await record_audit(
        db, action="DSAR_CREATED", user_id=current_user.id,
        resource_type="data_subject_request", resource_id=None,
        description=f"DSAR submitted: {body.request_type.value}",
        ip_address=_client_ip(request),
    )
    await db.commit()
    await db.refresh(dsar)
    return dsar


@router.get("/requests", response_model=List[DSARResponse])
async def my_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DataSubjectRequest)
        .where(DataSubjectRequest.user_id == current_user.id)
        .order_by(DataSubjectRequest.created_at.desc())
    )
    return result.scalars().all()


# --------------------------------------------------------------------------
# Administration / DPO
# --------------------------------------------------------------------------
@router.get("/requests/all", response_model=List[DSARResponse])
async def all_requests(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DataSubjectRequest).order_by(DataSubjectRequest.created_at.desc())
    )
    return result.scalars().all()


@router.post("/requests/{request_id}/process", response_model=DSARResponse)
async def process_dsar(
    request_id: int,
    body: DSARProcess,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Handle a DSAR. Completing an erasure request anonymizes the subject
    (unless a legal hold applies); completing a restriction sets the flag."""
    dsar = (
        await db.execute(select(DataSubjectRequest).where(DataSubjectRequest.id == request_id))
    ).scalar_one_or_none()
    if not dsar:
        raise HTTPException(status_code=404, detail="Request not found")

    dsar.status = body.status
    dsar.resolution_notes = body.resolution_notes
    dsar.handled_by = current_user.id

    performed = "status updated"
    if body.status == DSARStatus.COMPLETED:
        dsar.completed_at = datetime.now(timezone.utc)
        subject = (
            await db.execute(select(User).where(User.id == dsar.user_id))
        ).scalar_one_or_none()

        if dsar.request_type == DSARType.ERASURE:
            if dsar.legal_hold:
                raise HTTPException(
                    status_code=409,
                    detail="Cannot erase: record is under AML legal hold",
                )
            if subject:
                await anonymize_user(db, subject)
                performed = "subject anonymized"
        elif dsar.request_type == DSARType.RESTRICTION and subject:
            from app.models.client import ClientProfile
            profile = (
                await db.execute(select(ClientProfile).where(ClientProfile.user_id == subject.id))
            ).scalar_one_or_none()
            if profile:
                profile.processing_restricted = True
                db.add(profile)
            performed = "processing restricted"

    db.add(dsar)
    await record_audit(
        db, action="DSAR_PROCESSED", user_id=current_user.id,
        resource_type="data_subject_request", resource_id=dsar.id,
        description=f"{dsar.request_type.value} -> {body.status.value} ({performed})",
        ip_address=_client_ip(request),
    )
    await db.commit()
    await db.refresh(dsar)
    return dsar


@router.post("/retention/purge")
async def run_retention_purge(
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Anonymize profiles whose retention period has lapsed (Art.5(1)(e))."""
    result = await purge_expired_data(db)
    await record_audit(
        db, action="RETENTION_PURGE", user_id=current_user.id,
        resource_type="client_profile", resource_id=None,
        description=f"Retention purge: {result}",
        ip_address=_client_ip(request),
    )
    await db.commit()
    return result


@router.get("/audit/integrity")
async def audit_integrity(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Verify the audit-log hash chain (tamper detection)."""
    return await verify_audit_chain(db)
