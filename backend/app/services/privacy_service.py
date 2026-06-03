"""GDPR data-subject operations: export, erasure/anonymization, retention purge."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.client import ClientProfile
from app.models.document import Document
from app.models.transaction import Transaction
from app.models.privacy import Consent, DataSubjectRequest

REDACTED = "REDACTED"


def _iso(dt) -> Optional[str]:
    return dt.isoformat() if dt else None


async def export_subject_data(db: AsyncSession, user: User) -> dict:
    """Build a machine-readable copy of all personal data held about a user
    (GDPR Art.15 access / Art.20 portability)."""
    profile = (
        await db.execute(select(ClientProfile).where(ClientProfile.user_id == user.id))
    ).scalar_one_or_none()

    export: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "account": {
            "id": user.id, "email": user.email, "full_name": user.full_name,
            "role": user.role.value, "is_active": user.is_active,
            "created_at": _iso(user.created_at), "last_login": _iso(user.last_login),
        },
        "profile": None,
        "documents": [],
        "transactions": [],
        "consents": [],
        "data_subject_requests": [],
    }

    if profile:
        export["profile"] = {
            c.name: (lambda v: v.isoformat() if isinstance(v, datetime) else v)(getattr(profile, c.name))
            for c in ClientProfile.__table__.columns
        }

        docs = (await db.execute(select(Document).where(Document.client_id == profile.id))).scalars().all()
        export["documents"] = [
            {"id": d.id, "document_type": d.document_type.value if d.document_type else None,
             "original_filename": d.original_filename, "status": d.status.value if d.status else None,
             "created_at": _iso(d.created_at)} for d in docs
        ]

        txns = (await db.execute(select(Transaction).where(Transaction.client_id == profile.id))).scalars().all()
        export["transactions"] = [
            {"transaction_ref": t.transaction_ref, "type": t.type.value if t.type else None,
             "amount": t.amount, "currency": t.currency,
             "transaction_date": _iso(t.transaction_date)} for t in txns
        ]

    consents = (await db.execute(select(Consent).where(Consent.user_id == user.id))).scalars().all()
    export["consents"] = [
        {"purpose": c.purpose, "policy_version": c.policy_version, "granted": c.granted,
         "granted_at": _iso(c.granted_at), "revoked_at": _iso(c.revoked_at)} for c in consents
    ]

    dsars = (await db.execute(select(DataSubjectRequest).where(DataSubjectRequest.user_id == user.id))).scalars().all()
    export["data_subject_requests"] = [
        {"id": r.id, "request_type": r.request_type.value, "status": r.status.value,
         "created_at": _iso(r.created_at), "completed_at": _iso(r.completed_at)} for r in dsars
    ]

    return export


async def anonymize_user(db: AsyncSession, user: User) -> None:
    """Irreversibly strip personal data while keeping AML-relevant aggregates
    (anonymization rather than hard delete — GDPR Art.17 with AML retention)."""
    profile = (
        await db.execute(select(ClientProfile).where(ClientProfile.user_id == user.id))
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if profile:
        profile.first_name = REDACTED
        profile.last_name = REDACTED
        profile.middle_name = None
        profile.date_of_birth = None
        profile.gender = None
        profile.nationality = None
        profile.country_of_birth = None
        profile.phone_number = None
        profile.address_line1 = None
        profile.address_line2 = None
        profile.city = None
        profile.state_province = None
        profile.postal_code = None
        profile.id_type = None
        profile.id_number = None
        profile.id_issuing_country = None
        profile.occupation = None
        profile.employer_name = None
        profile.source_of_funds = None
        profile.source_of_wealth = None
        profile.pep_details = None
        profile.ip_address = None
        profile.device_fingerprint = None
        profile.processing_restricted = True
        profile.anonymized_at = now
        db.add(profile)

    # Break the link to identity at the account level.
    user.email = f"anonymized+{user.id}@deleted.local"
    user.full_name = REDACTED
    user.is_active = False
    user.mfa_secret = None
    db.add(user)


async def purge_expired_data(db: AsyncSession) -> dict:
    """Anonymize profiles whose retention period has lapsed (Art.5(1)(e))."""
    now = datetime.now(timezone.utc)
    profiles = (
        await db.execute(
            select(ClientProfile).where(
                ClientProfile.retention_until.is_not(None),
                ClientProfile.anonymized_at.is_(None),
            )
        )
    ).scalars().all()

    purged = 0
    for profile in profiles:
        retention = profile.retention_until
        if retention is not None and retention.tzinfo is None:
            retention = retention.replace(tzinfo=timezone.utc)
        if retention is not None and retention < now:
            user = (
                await db.execute(select(User).where(User.id == profile.user_id))
            ).scalar_one_or_none()
            if user:
                await anonymize_user(db, user)
                purged += 1

    return {"purged": purged, "checked": len(profiles)}
