from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.deps import require_analyst, require_compliance
from app.models.user import User, UserRole
from app.models.incident import (
    IncidentTicket, IncidentComment, IncidentAssignment, RiskAssessment, FalsePositive,
    TicketStatus, TicketPriority, IncidentClassification,
)
from app.schemas.incident import (
    IncidentTicketResponse, IncidentTicketDetail, AssignRequest, StatusUpdate,
    IncidentCommentCreate, IncidentCommentResponse, RiskAssessmentCreate,
    RiskAssessmentResponse, ClassifyRequest,
)

router = APIRouter(prefix="/incidents", tags=["Incident Management"])


async def _get_ticket(ticket_id: int, db: AsyncSession) -> IncidentTicket:
    result = await db.execute(
        select(IncidentTicket)
        .where(IncidentTicket.id == ticket_id)
        .options(
            selectinload(IncidentTicket.comments),
            selectinload(IncidentTicket.assignments),
            selectinload(IncidentTicket.risk_assessments),
            selectinload(IncidentTicket.false_positive),
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Incident ticket not found")
    return ticket


def _ensure_can_act(user: User, ticket: IncidentTicket) -> None:
    """ABAC: a risk analyst may only act on tickets assigned to them (or unassigned).
    Compliance officers and admins are not restricted (segregation of duties)."""
    if user.role == UserRole.RISK_ANALYST and ticket.assigned_analyst_id not in (None, user.id):
        raise HTTPException(
            status_code=403,
            detail="This ticket is assigned to another analyst",
        )


@router.get("/", response_model=List[IncidentTicketResponse])
async def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[TicketStatus] = None,
    priority: Optional[TicketPriority] = None,
    classification: Optional[IncidentClassification] = None,
    assigned_to_me: bool = False,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    query = select(IncidentTicket)
    if status:
        query = query.where(IncidentTicket.status == status)
    if priority:
        query = query.where(IncidentTicket.priority == priority)
    if classification:
        query = query.where(IncidentTicket.classification == classification)
    if assigned_to_me:
        query = query.where(IncidentTicket.assigned_analyst_id == current_user.id)
    query = query.order_by(IncidentTicket.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/meta/analysts")
async def list_analysts(
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Users who can own a ticket (for assignment dropdowns)."""
    result = await db.execute(
        select(User).where(
            User.role.in_([UserRole.RISK_ANALYST, UserRole.COMPLIANCE_OFFICER, UserRole.ADMIN]),
            User.is_active == True,
        )
    )
    return [{"id": u.id, "full_name": u.full_name, "role": u.role.value} for u in result.scalars().all()]


@router.get("/{ticket_id}", response_model=IncidentTicketDetail)
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    return await _get_ticket(ticket_id, db)


@router.post("/{ticket_id}/assign", response_model=IncidentTicketResponse)
async def assign_ticket(
    ticket_id: int,
    body: AssignRequest,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    ticket = await _get_ticket(ticket_id, db)
    ticket.assigned_analyst_id = body.assigned_to
    if not ticket.first_assigned_at:
        ticket.first_assigned_at = datetime.utcnow()
    if ticket.status == TicketStatus.NEW:
        ticket.status = TicketStatus.ASSIGNED
    db.add(IncidentAssignment(
        ticket_id=ticket.id, assigned_to=body.assigned_to,
        assigned_by=current_user.id, note=body.note,
    ))
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.put("/{ticket_id}/status", response_model=IncidentTicketResponse)
async def update_status(
    ticket_id: int,
    body: StatusUpdate,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    ticket = await _get_ticket(ticket_id, db)
    _ensure_can_act(current_user, ticket)
    ticket.status = body.status
    if body.resolution_notes is not None:
        ticket.resolution_notes = body.resolution_notes
    if body.status == TicketStatus.CLOSED:
        if not ticket.closed_at:
            ticket.closed_at = datetime.utcnow()
    else:
        # Reopening a previously closed ticket — clear the closure timestamp.
        ticket.closed_at = None
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/escalate", response_model=IncidentTicketResponse)
async def escalate_ticket(
    ticket_id: int,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    ticket = await _get_ticket(ticket_id, db)
    _ensure_can_act(current_user, ticket)
    ticket.status = TicketStatus.ESCALATED
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/comments", response_model=IncidentCommentResponse, status_code=201)
async def add_comment(
    ticket_id: int,
    body: IncidentCommentCreate,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    ticket = await _get_ticket(ticket_id, db)
    _ensure_can_act(current_user, ticket)
    comment = IncidentComment(ticket_id=ticket_id, author_id=current_user.id, comment=body.comment)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


@router.post("/{ticket_id}/risk-assessment", response_model=RiskAssessmentResponse, status_code=201)
async def add_risk_assessment(
    ticket_id: int,
    body: RiskAssessmentCreate,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    ticket = await _get_ticket(ticket_id, db)
    _ensure_can_act(current_user, ticket)
    assessment = RiskAssessment(
        ticket_id=ticket_id, assessor_id=current_user.id, **body.model_dump()
    )
    db.add(assessment)
    # The latest assessment drives the ticket's risk level
    ticket.risk_level = body.risk_level
    if ticket.status in (TicketStatus.NEW, TicketStatus.ASSIGNED):
        ticket.status = TicketStatus.IN_PROGRESS
    db.add(ticket)
    await db.commit()
    await db.refresh(assessment)
    return assessment


@router.post("/{ticket_id}/classify", response_model=IncidentTicketDetail)
async def classify_ticket(
    ticket_id: int,
    body: ClassifyRequest,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    ticket = await _get_ticket(ticket_id, db)
    _ensure_can_act(current_user, ticket)
    ticket.classification = body.classification
    if body.resolution_notes is not None:
        ticket.resolution_notes = body.resolution_notes

    if body.classification == IncidentClassification.FALSE_POSITIVE:
        if not body.reason:
            raise HTTPException(status_code=400, detail="A false-positive reason is required")
        if ticket.false_positive is None:
            db.add(FalsePositive(
                ticket_id=ticket.id,
                classified_by=current_user.id,
                detection_rule_id=ticket.detection_rule_id,
                reason=body.reason,
                root_cause=body.root_cause,
                source_system=body.source_system or ticket.alert_source,
                analyst_comments=body.analyst_comments,
                suggested_rule_tuning=body.suggested_rule_tuning,
            ))

    ticket.status = TicketStatus.CLOSED
    if not ticket.closed_at:
        ticket.closed_at = datetime.utcnow()
    db.add(ticket)
    await db.commit()
    return await _get_ticket(ticket_id, db)
