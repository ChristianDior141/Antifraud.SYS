from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.deps import require_compliance
from app.models.user import User
from app.models.client import ClientProfile, KYCStatus
from app.models.review import Review, ReviewDecision
from app.models.audit import AuditLog, Notification
from pydantic import BaseModel

router = APIRouter(prefix="/reviews", tags=["Compliance Reviews"])


class ReviewCreate(BaseModel):
    client_id: int
    notes: Optional[str] = None


class ReviewDecisionIn(BaseModel):
    decision: ReviewDecision
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    required_documents: Optional[str] = None


@router.post("/", status_code=201)
async def create_review(
    review_in: ReviewCreate,
    current_user: User = Depends(require_compliance),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ClientProfile).where(ClientProfile.id == review_in.client_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Client not found")

    review = Review(
        client_id=review_in.client_id,
        reviewer_id=current_user.id,
        notes=review_in.notes,
    )
    db.add(review)
    profile.kyc_status = KYCStatus.PENDING_REVIEW
    db.add(profile)
    await db.commit()
    await db.refresh(review)
    return {"id": review.id, "status": "review_started"}


@router.put("/{review_id}/decide")
async def decide_review(
    review_id: int,
    decision_in: ReviewDecisionIn,
    current_user: User = Depends(require_compliance),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.decision = decision_in.decision
    review.notes = decision_in.notes
    review.rejection_reason = decision_in.rejection_reason
    review.required_documents = decision_in.required_documents
    review.is_complete = True
    review.completed_at = datetime.utcnow()
    db.add(review)

    # Update client KYC status
    client_result = await db.execute(
        select(ClientProfile).where(ClientProfile.id == review.client_id)
    )
    profile = client_result.scalar_one_or_none()
    if profile:
        status_map = {
            ReviewDecision.APPROVED: KYCStatus.APPROVED,
            ReviewDecision.REJECTED: KYCStatus.REJECTED,
            ReviewDecision.REQUEST_MORE_INFO: KYCStatus.REQUIRES_UPDATE,
            ReviewDecision.ESCALATED: KYCStatus.PENDING_REVIEW,
        }
        profile.kyc_status = status_map[decision_in.decision]
        db.add(profile)

        notif = Notification(
            user_id=profile.user_id,
            title=f"KYC Review {decision_in.decision.value.title()}",
            message=f"Your KYC review has been {decision_in.decision.value}. "
                    + (decision_in.notes or ""),
            notification_type="kyc_update",
        )
        db.add(notif)

    log = AuditLog(
        user_id=current_user.id,
        action="KYC_REVIEW_DECISION",
        resource_type="review",
        resource_id=review_id,
        description=f"Decision: {decision_in.decision.value}",
    )
    db.add(log)
    await db.commit()
    return {"message": "Decision recorded", "decision": decision_in.decision}


@router.get("/pending")
async def get_pending_reviews(
    current_user: User = Depends(require_compliance),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClientProfile).where(ClientProfile.kyc_status == KYCStatus.PENDING_REVIEW)
    )
    return result.scalars().all()
