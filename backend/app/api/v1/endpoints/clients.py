from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from app.core.database import get_db
from app.core.deps import get_current_user, require_compliance, require_analyst
from app.models.user import User, UserRole
from app.models.client import ClientProfile, KYCStatus
from app.models.risk import RiskScore
from app.schemas.client import ClientProfileCreate, ClientProfileUpdate, ClientProfileResponse, ClientListResponse
from app.services.risk_engine import calculate_risk_score
from app.services.audit_service import log_pii_access

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("/profile", response_model=ClientProfileResponse, status_code=201)
async def create_profile(
    profile_in: ClientProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClientProfile).where(ClientProfile.user_id == current_user.id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Profile already exists")

    profile = ClientProfile(user_id=current_user.id, **profile_in.model_dump())
    db.add(profile)
    await db.flush()
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/profile/me", response_model=ClientProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClientProfile).where(ClientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/profile/me", response_model=ClientProfileResponse)
async def update_my_profile(
    updates: ClientProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClientProfile).where(ClientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    for field, value in updates.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/", response_model=List[ClientListResponse])
async def list_clients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    kyc_status: Optional[KYCStatus] = None,
    risk_level: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_compliance),
    db: AsyncSession = Depends(get_db),
):
    query = select(ClientProfile)
    if kyc_status:
        query = query.where(ClientProfile.kyc_status == kyc_status)
    if risk_level:
        query = query.where(ClientProfile.risk_level == risk_level)
    if search:
        query = query.where(
            (ClientProfile.first_name.ilike(f"%{search}%"))
            | (ClientProfile.last_name.ilike(f"%{search}%"))
        )
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{client_id}", response_model=ClientProfileResponse)
async def get_client(
    client_id: int,
    request: Request,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ClientProfile).where(ClientProfile.id == client_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Client not found")
    # GDPR Art.30 / ISO A.12.4.1 — record staff access to personal data.
    await log_pii_access(
        db, user_id=current_user.id, resource_type="client_profile",
        resource_id=client_id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return profile


@router.post("/{client_id}/risk-score")
async def trigger_risk_assessment(
    client_id: int,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ClientProfile).where(ClientProfile.id == client_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Client not found")

    risk = await calculate_risk_score(profile, db)
    await db.commit()
    return {"client_id": client_id, "risk_score": risk.total_score, "risk_level": risk.risk_level}


def _serialize_risk(risk: RiskScore) -> dict:
    return {
        "client_id": risk.client_id,
        "total_score": risk.total_score,
        "risk_level": risk.risk_level,
        "components": {
            "personal": risk.personal_risk_score,
            "geographic": risk.geographic_risk_score,
            "transaction": risk.transaction_risk_score,
            "behavioral": risk.behavioral_risk_score,
            "document": risk.document_risk_score,
        },
        "flags": {
            "pep": risk.pep_flag,
            "sanctions": risk.sanctions_flag,
            "high_risk_country": risk.high_risk_country_flag,
            "unusual_transaction": risk.unusual_transaction_flag,
        },
        "factors": (risk.risk_factors or {}).get("factors", []),
        "calculated_at": risk.calculated_at.isoformat() if risk.calculated_at else None,
    }


@router.get("/{client_id}/risk-assessment")
async def get_risk_assessment(
    client_id: int,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Return the latest stored risk assessment (with factor explanations).
    Computes one on the fly if none exists yet."""
    result = await db.execute(select(ClientProfile).where(ClientProfile.id == client_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Client not found")

    latest = await db.execute(
        select(RiskScore)
        .where(RiskScore.client_id == client_id)
        .order_by(RiskScore.id.desc())
        .limit(1)
    )
    risk = latest.scalar_one_or_none()

    if not risk:
        risk = await calculate_risk_score(profile, db)
        await db.commit()

    return _serialize_risk(risk)
