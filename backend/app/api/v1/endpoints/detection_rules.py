from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.core.deps import require_analyst, require_admin
from app.models.user import User
from app.models.detection_rule import DetectionRule, RuleTuningHistory
from app.models.incident import FalsePositive, IncidentTicket
from app.schemas.detection_rule import (
    DetectionRuleResponse, DetectionRuleDetail, DetectionRuleStats,
    RuleTuningHistoryResponse, RuleTuneRequest,
)
from app.schemas.incident import FalsePositiveResponse
from app.services.incident_service import compute_rule_stats, suggest_improvements

router = APIRouter(prefix="/detection-rules", tags=["Detection Rule Tuning"])


async def _serialize_rule(rule: DetectionRule, db: AsyncSession) -> DetectionRuleResponse:
    stats = await compute_rule_stats(rule, db)
    data = DetectionRuleResponse.model_validate(rule)
    data.stats = DetectionRuleStats(**stats)
    return data


@router.get("/", response_model=List[DetectionRuleResponse])
async def list_rules(
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(DetectionRule).order_by(DetectionRule.rule_code))
    rules = result.scalars().all()
    return [await _serialize_rule(r, db) for r in rules]


@router.get("/{rule_id}", response_model=DetectionRuleDetail)
async def get_rule(
    rule_id: int,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DetectionRule)
        .where(DetectionRule.id == rule_id)
        .options(selectinload(DetectionRule.tuning_history))
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Detection rule not found")

    stats = await compute_rule_stats(rule, db)
    fps = await db.execute(
        select(FalsePositive).where(FalsePositive.detection_rule_id == rule.id)
    )
    fp_reasons = [
        (f.reason.value if hasattr(f.reason, "value") else str(f.reason))
        for f in fps.scalars().all()
    ]

    detail = DetectionRuleDetail.model_validate(rule)
    detail.stats = DetectionRuleStats(**stats)
    detail.suggested_improvements = suggest_improvements(stats, fp_reasons)
    return detail


@router.get("/{rule_id}/false-positives", response_model=List[FalsePositiveResponse])
async def rule_false_positives(
    rule_id: int,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FalsePositive)
        .where(FalsePositive.detection_rule_id == rule_id)
        .order_by(FalsePositive.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{rule_id}/history", response_model=List[RuleTuningHistoryResponse])
async def rule_history(
    rule_id: int,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RuleTuningHistory)
        .where(RuleTuningHistory.rule_id == rule_id)
        .order_by(RuleTuningHistory.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{rule_id}/tune", response_model=DetectionRuleDetail)
async def tune_rule(
    rule_id: int,
    body: RuleTuneRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(DetectionRule).where(DetectionRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Detection rule not found")

    old_params = rule.parameters
    new_version = (rule.version or 1) + 1
    db.add(RuleTuningHistory(
        rule_id=rule.id,
        changed_by=current_user.id,
        version=new_version,
        change_description=body.change_description,
        old_parameters=old_params,
        new_parameters=body.new_parameters,
    ))
    rule.parameters = body.new_parameters
    rule.version = new_version
    if body.is_active is not None:
        rule.is_active = body.is_active
    rule.updated_at = datetime.utcnow()
    db.add(rule)
    await db.commit()

    # Return refreshed detail
    return await get_rule(rule_id, current_user, db)
