import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.deps import get_current_user, require_analyst
from app.models.user import User
from app.models.client import ClientProfile
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.transaction import TransactionCreate, TransactionResponse
from app.services.aml_monitor import evaluate_transaction
from app.services.incident_service import create_ticket_for_alert

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("/", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    txn_in: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClientProfile).where(ClientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Client profile required")

    txn = Transaction(
        client_id=profile.id,
        transaction_ref=f"TXN-{uuid.uuid4().hex[:12].upper()}",
        status=TransactionStatus.PENDING,
        **txn_in.model_dump(),
    )
    db.add(txn)
    await db.flush()

    # Run AML checks, then open an incident ticket for each generated alert
    alerts = await evaluate_transaction(profile, txn, db)
    for alert in alerts:
        await create_ticket_for_alert(alert, db)

    txn.status = TransactionStatus.COMPLETED if not txn.is_flagged else TransactionStatus.FLAGGED
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return txn


@router.get("/my", response_model=List[TransactionResponse])
async def get_my_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClientProfile).where(ClientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return []

    txns = await db.execute(
        select(Transaction)
        .where(Transaction.client_id == profile.id)
        .order_by(Transaction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return txns.scalars().all()


@router.get("/client/{client_id}", response_model=List[TransactionResponse])
async def get_client_transactions(
    client_id: int,
    flagged_only: bool = False,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    query = select(Transaction).where(Transaction.client_id == client_id)
    if flagged_only:
        query = query.where(Transaction.is_flagged == True)
    result = await db.execute(query.order_by(Transaction.created_at.desc()))
    return result.scalars().all()


@router.get("/stats/summary")
async def transaction_summary(
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    total = await db.execute(select(func.count(Transaction.id)))
    flagged = await db.execute(
        select(func.count(Transaction.id)).where(Transaction.is_flagged == True)
    )
    volume = await db.execute(select(func.sum(Transaction.amount)))
    return {
        "total_transactions": total.scalar() or 0,
        "flagged_transactions": flagged.scalar() or 0,
        "total_volume": float(volume.scalar() or 0),
    }
