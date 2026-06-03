"""
Seed script — populates the database with realistic demo data.
Run: python seed_data.py
"""
import asyncio
import random
import uuid
from datetime import datetime, timedelta, date
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.client import ClientProfile, KYCStatus, RiskLevel
from app.models.document import Document, DocumentType, DocumentStatus
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.aml import AMLAlert, AlertType, AlertSeverity, AlertStatus
from app.models.risk import RiskScore
from app.models.detection_rule import DetectionRule, RuleTuningHistory
from app.models.incident import (
    IncidentTicket, IncidentComment, IncidentAssignment, RiskAssessment, FalsePositive,
    TicketStatus, TicketPriority, IncidentClassification, FalsePositiveReason,
)
from app.services.explanation_templates import render_flag_reason, combine_flag_reasons, render_aml
from app.services.incident_service import RULE_REGISTRY, create_ticket_for_alert
from sqlalchemy import select

LARGE_TRANSACTION_THRESHOLD = 50_000
PEP_MATERIALITY_THRESHOLD = 10_000
RAPID_MOVEMENT_HOURS = 2
RAPID_MOVEMENT_COUNT = 6  # transactions in the burst (>= engine's threshold of 5)

fake = Faker()
random.seed(42)

# Distribute demo data across the last ~6 months so time-series charts look realistic.
SEED_WINDOW_DAYS = 180


def random_datetime_within(days_back: int = SEED_WINDOW_DAYS) -> datetime:
    """Random datetime uniformly distributed across the last `days_back` days."""
    now = datetime.utcnow()
    offset = timedelta(
        days=random.randint(0, days_back),
        seconds=random.randint(0, 86399),
    )
    return now - offset


def random_datetime_between(start: datetime, end: datetime) -> datetime:
    """Random datetime between two points (inclusive)."""
    if end <= start:
        return start
    delta_seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, delta_seconds))

NATIONALITIES = ["US", "GB", "DE", "FR", "JP", "CA", "AU", "SG", "AE", "IN",
                 "RU", "IR", "KP", "VE", "BY"]  # mix of normal and high-risk
HIGH_RISK_COUNTRIES = ["IR", "KP", "VE", "BY", "RU"]  # FATF high-risk jurisdictions (demo)

STAFF_USERS = [
    {"email": "admin@kyc-platform.com", "name": "System Administrator", "role": UserRole.ADMIN},
    {"email": "compliance1@kyc-platform.com", "name": "Sarah Johnson", "role": UserRole.COMPLIANCE_OFFICER},
    {"email": "compliance2@kyc-platform.com", "name": "Michael Chen", "role": UserRole.COMPLIANCE_OFFICER},
    {"email": "analyst1@kyc-platform.com", "name": "Emma Davis", "role": UserRole.RISK_ANALYST},
    {"email": "analyst2@kyc-platform.com", "name": "James Wilson", "role": UserRole.RISK_ANALYST},
]


# Rules that the seed's alerts reference but which aren't in the canonical registry
EXTRA_RULES = [
    {"rule_code": "ELEVATED_RISK_PROFILE", "name": "Elevated Risk Profile",
     "alert_type": "unusual_frequency", "parameters": {},
     "description": "Client carries an elevated inherent risk profile."},
    {"rule_code": "AUTO_DETECTION", "name": "Automated Detection",
     "alert_type": "unusual_frequency", "parameters": {},
     "description": "Generic automated monitoring trigger."},
]

FP_ROOT_CAUSES = {
    FalsePositiveReason.THRESHOLD_TOO_SENSITIVE: "Threshold set too low for this client segment.",
    FalsePositiveReason.INCORRECT_CORRELATION_RULE: "Correlation logic matched unrelated activity.",
    FalsePositiveReason.WHITELISTED_ACTIVITY: "Counterparty is an approved, whitelisted partner.",
    FalsePositiveReason.LEGITIMATE_USER_BEHAVIOR: "Activity consistent with the client's declared profile.",
    FalsePositiveReason.DATA_QUALITY_ISSUE: "Stale/incorrect reference data triggered the match.",
    FalsePositiveReason.CONFIGURATION_ERROR: "Rule parameter was misconfigured.",
    FalsePositiveReason.OTHER: "Reviewed and deemed not suspicious.",
}


async def seed_detection_rules(db: AsyncSession):
    have = set((await db.execute(select(DetectionRule.rule_code))).scalars().all())
    for spec in list(RULE_REGISTRY) + EXTRA_RULES:
        if spec["rule_code"] in have:
            continue
        db.add(DetectionRule(
            rule_code=spec["rule_code"], name=spec["name"],
            description=spec.get("description"), alert_type=spec.get("alert_type"),
            parameters=spec.get("parameters"), version=1, is_active=True,
        ))
    await db.flush()


async def seed_incidents(db: AsyncSession, staff):
    analysts = [u for u in staff if u.role in (UserRole.RISK_ANALYST, UserRole.COMPLIANCE_OFFICER)]
    admin = next((u for u in staff if u.role == UserRole.ADMIN), staff[0])
    if not analysts:
        analysts = [admin]

    alerts = (await db.execute(select(AMLAlert).order_by(AMLAlert.created_at))).scalars().all()
    now = datetime.utcnow()
    reasons = list(FalsePositiveReason)

    for alert in alerts:
        ticket = await create_ticket_for_alert(alert, db)
        if ticket is None:
            continue
        created = alert.created_at.replace(tzinfo=None) if alert.created_at else now
        ticket.created_at = created  # align ticket age with the alert for MTTR/trend

        months_ago = max(0.0, (now - created).days / 30.0)
        # Older incidents have a higher FP share → FP rate declines over time.
        fp_prob = min(0.6, 0.12 + 0.08 * months_ago)

        assignee = random.choice(analysts)
        if random.random() < 0.85:
            ticket.assigned_analyst_id = assignee.id
            ticket.first_assigned_at = min(now, created + timedelta(minutes=random.randint(20, 1200)))
            ticket.status = TicketStatus.ASSIGNED
            db.add(IncidentAssignment(
                ticket_id=ticket.id, assigned_to=assignee.id, assigned_by=admin.id,
                note="Assigned for investigation", created_at=ticket.first_assigned_at,
            ))
            db.add(IncidentComment(
                ticket_id=ticket.id, author_id=assignee.id,
                comment=random.choice([
                    "Picked up for review.", "Requested supporting documentation.",
                    "Reviewing counterparty and transaction context.",
                ]),
                created_at=ticket.first_assigned_at + timedelta(minutes=random.randint(5, 180)),
            ))

        if random.random() < 0.7:  # resolved
            if not ticket.first_assigned_at:
                ticket.first_assigned_at = min(now, created + timedelta(minutes=random.randint(20, 300)))
            closed = min(now, created + timedelta(hours=random.uniform(2, 120)))
            ticket.closed_at = closed
            ticket.status = TicketStatus.CLOSED

            db.add(RiskAssessment(
                ticket_id=ticket.id, assessor_id=assignee.id, risk_level=ticket.risk_level,
                business_impact=random.choice(["Minimal", "Moderate", "Significant"]),
                financial_impact=round(random.uniform(0, 250000), 2),
                technical_impact=random.choice(["None", "Monitoring rule reviewed"]),
                confidence_score=round(random.uniform(60, 99), 1),
                recommended_action=random.choice([
                    "Close — no further action.", "File SAR.", "Apply enhanced due diligence.",
                ]),
                created_at=min(now, created + timedelta(hours=random.uniform(1, 48))),
            ))

            if random.random() < fp_prob:
                ticket.classification = IncidentClassification.FALSE_POSITIVE
                reason = random.choice(reasons)
                db.add(FalsePositive(
                    ticket_id=ticket.id, classified_by=assignee.id,
                    detection_rule_id=ticket.detection_rule_id, reason=reason,
                    root_cause=FP_ROOT_CAUSES[reason], source_system="AML Monitor",
                    analyst_comments="Reviewed; not suspicious.",
                    suggested_rule_tuning="Consider adjusting thresholds / adding exception.",
                    created_at=closed,
                ))
                ticket.resolution_notes = "Closed as false positive after investigation."
            else:
                ticket.classification = IncidentClassification.REAL_INCIDENT
                ticket.resolution_notes = "Confirmed suspicious activity; recorded as incident."
        else:  # remain open
            ticket.status = random.choice([
                TicketStatus.NEW, TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS,
                TicketStatus.UNDER_REVIEW, TicketStatus.ESCALATED,
            ])
        db.add(ticket)

    await db.flush()

    # Dated rule-tuning history — correlates with the FP-rate decline.
    rules = {r.rule_code: r for r in (await db.execute(select(DetectionRule))).scalars().all()}
    tuning_specs = [
        ("LARGE_TRANSACTION", 5, "Raised large-transaction threshold to cut noise",
         {"threshold": 50000}, {"threshold": 60000}),
        ("VELOCITY_CHECK", 4, "Increased velocity count threshold",
         {"count": 10, "window_hours": 24}, {"count": 15, "window_hours": 24}),
        ("STRUCTURING_DETECTION", 3, "Tightened structuring band and min count",
         {"min_count": 3}, {"min_count": 4}),
        ("HIGH_RISK_JURISDICTION", 2, "Added approved-counterparty whitelist",
         {}, {"whitelist_enabled": True}),
    ]
    for code, months_back, desc, old, new in tuning_specs:
        r = rules.get(code)
        if not r:
            continue
        r.version = (r.version or 1) + 1
        db.add(RuleTuningHistory(
            rule_id=r.id, changed_by=admin.id, version=r.version,
            change_description=desc, old_parameters=old, new_parameters=new,
            created_at=now - timedelta(days=months_back * 30 - 5),
        ))
        r.parameters = new
        db.add(r)
    await db.flush()


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        print("Seeding staff users...")
        staff = []
        for s in STAFF_USERS:
            user = User(
                email=s["email"],
                full_name=s["name"],
                hashed_password=get_password_hash("Admin123!@#"),
                role=s["role"],
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            staff.append(user)
        await db.flush()

        print("Seeding client users and profiles...")
        for i in range(50):
            nationality = random.choice(NATIONALITIES)
            is_high_risk = nationality in {"RU", "IR", "KP", "VE", "BY"}
            is_pep = random.random() < 0.08
            is_sanctioned = random.random() < 0.04          # rare — critical cases
            anomalous_devices = random.random() < 0.15       # many devices/IPs (behavioral)
            rapid_mover = random.random() < 0.10             # exhibits a rapid in/out burst
            declared_types = random.sample(
                [t.value for t in TransactionType], k=random.randint(2, 3))

            kyc_status = random.choice([
                KYCStatus.APPROVED, KYCStatus.APPROVED, KYCStatus.APPROVED,
                KYCStatus.PENDING_REVIEW, KYCStatus.REJECTED, KYCStatus.IN_PROGRESS,
            ])
            risk_score = random.uniform(5, 95)
            if is_pep or is_high_risk or is_sanctioned:
                risk_score = min(risk_score + 30, 100)

            if risk_score <= 30:
                risk_level = RiskLevel.LOW
            elif risk_score <= 60:
                risk_level = RiskLevel.MEDIUM
            elif risk_score <= 80:
                risk_level = RiskLevel.HIGH
            else:
                risk_level = RiskLevel.CRITICAL

            # When this client onboarded — spread across the last 6 months
            client_created = random_datetime_within()

            user = User(
                email=fake.unique.email(),
                full_name=fake.name(),
                hashed_password=get_password_hash("Client123!"),
                role=UserRole.CLIENT,
                is_active=True,
                is_verified=kyc_status == KYCStatus.APPROVED,
                created_at=client_created,
            )
            db.add(user)
            await db.flush()

            dob = fake.date_of_birth(minimum_age=18, maximum_age=75)
            profile = ClientProfile(
                user_id=user.id,
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                date_of_birth=dob,
                nationality=nationality,
                country_of_residence=nationality,
                phone_number=fake.phone_number()[:20],
                address_line1=fake.street_address(),
                city=fake.city(),
                country=nationality,
                id_type="passport",
                id_number=fake.bothify("??#######").upper(),
                occupation=fake.job()[:100],
                source_of_funds=random.choice(["salary", "business", "investment", "inheritance"]),
                annual_income_range=random.choice(["0-30k", "30k-75k", "75k-150k", "150k+"]),
                expected_monthly_transaction_volume=random.uniform(1000, 50000),
                expected_transaction_types=declared_types,
                is_pep=is_pep,
                is_sanctioned=is_sanctioned,
                is_high_risk_country=is_high_risk,
                kyc_status=kyc_status,
                risk_level=risk_level,
                risk_score=round(risk_score, 2),
                created_at=client_created,
            )
            db.add(profile)
            await db.flush()

            # Documents
            for doc_type in random.sample(list(DocumentType), k=random.randint(1, 3)):
                doc_status = DocumentStatus.APPROVED if kyc_status == KYCStatus.APPROVED else random.choice(
                    [DocumentStatus.PENDING, DocumentStatus.APPROVED, DocumentStatus.REJECTED]
                )
                doc = Document(
                    client_id=profile.id,
                    document_type=doc_type,
                    status=doc_status,
                    original_filename=f"{doc_type.value}_{fake.uuid4()[:8]}.pdf",
                    stored_filename=f"{fake.uuid4()}.pdf",
                    file_path=f"uploads/documents/{fake.uuid4()}.pdf",
                    file_size=random.randint(50000, 2000000),
                    mime_type="application/pdf",
                    created_at=random_datetime_between(client_created, datetime.utcnow()),
                )
                db.add(doc)

            # Stable device/IP for normal clients; anomalous clients use a fresh
            # one per transaction (drives the behavioral multiple-devices/IPs signals).
            stable_device = f"DEV-{uuid.uuid4().hex[:10]}"
            stable_ip = fake.ipv4_public()

            # Transactions
            num_txns = random.randint(1, 20)
            if anomalous_devices:
                num_txns = max(num_txns, 8)  # ensure enough to exceed device/IP thresholds
            for _ in range(num_txns):
                amount = random.uniform(100, 75000)
                cp_country = random.choice(NATIONALITIES)
                is_high_risk_country_txn = cp_country in HIGH_RISK_COUNTRIES
                pep_material = is_pep and amount >= PEP_MATERIALITY_THRESHOLD
                is_flagged = (
                    amount > 50000 or is_high_risk or is_high_risk_country_txn
                    or is_sanctioned or pep_material
                )

                # Determine a human-readable reason for the flag using shared templates.
                # Sanctions and PEP take priority so they become the primary alert.
                flag_reason = None
                triggered_rules = []
                if is_flagged:
                    reasons = []
                    if is_sanctioned:
                        triggered_rules.append("SANCTIONS_HIT")
                        reasons.append(render_flag_reason("SANCTIONS_HIT"))
                    if pep_material:
                        triggered_rules.append("PEP_TRANSACTION")
                        reasons.append(render_flag_reason("PEP_TRANSACTION"))
                    if amount > LARGE_TRANSACTION_THRESHOLD:
                        triggered_rules.append("LARGE_TRANSACTION")
                        reasons.append(render_flag_reason(
                            "LARGE_TRANSACTION", amount=amount, threshold=LARGE_TRANSACTION_THRESHOLD))
                    if is_high_risk_country_txn:
                        triggered_rules.append("HIGH_RISK_JURISDICTION")
                        reasons.append(render_flag_reason("HIGH_RISK_JURISDICTION", country=cp_country))
                    if is_high_risk:
                        triggered_rules.append("ELEVATED_RISK_PROFILE")
                        reasons.append(render_flag_reason("ELEVATED_RISK_PROFILE"))
                    flag_reason = combine_flag_reasons(reasons)

                # Transactions occur after the client onboarded, spread until now
                txn_dt = random_datetime_between(client_created, datetime.utcnow())

                txn = Transaction(
                    client_id=profile.id,
                    transaction_ref=f"TXN-{uuid.uuid4().hex[:12].upper()}",
                    type=random.choice(list(TransactionType)),
                    status=TransactionStatus.FLAGGED if is_flagged else TransactionStatus.COMPLETED,
                    amount=round(amount, 2),
                    currency="USD",
                    counterparty_name=fake.name(),
                    counterparty_country=cp_country,
                    description=fake.sentence(),
                    is_flagged=is_flagged,
                    flag_reason=flag_reason,
                    risk_score=round(min(100, amount / 1000 + (40 if is_high_risk else 0)), 1) if is_flagged else 0.0,
                    device_id=(f"DEV-{uuid.uuid4().hex[:10]}" if anomalous_devices else stable_device),
                    ip_address=(fake.ipv4_public() if anomalous_devices else stable_ip),
                    transaction_date=txn_dt,
                    created_at=txn_dt,
                )
                db.add(txn)
                await db.flush()

                # AML alerts for flagged transactions — text from shared templates.
                # Sanctions/PEP cases always raise an alert; others 60% of the time.
                if is_flagged and (is_sanctioned or pep_material or random.random() > 0.4):
                    # Pick the primary rule that fired for this transaction
                    rule_map = {
                        "SANCTIONS_HIT": AlertType.SANCTIONS_HIT,
                        "PEP_TRANSACTION": AlertType.PEP_TRANSACTION,
                        "LARGE_TRANSACTION": AlertType.LARGE_CASH,
                        "HIGH_RISK_JURISDICTION": AlertType.HIGH_RISK_JURISDICTION,
                        "ELEVATED_RISK_PROFILE": AlertType.UNUSUAL_FREQUENCY,
                    }
                    rule_code = triggered_rules[0] if triggered_rules else "AUTO_DETECTION"
                    alert_type = rule_map.get(rule_code, AlertType.UNUSUAL_FREQUENCY)
                    if rule_code == "SANCTIONS_HIT":
                        severity = AlertSeverity.CRITICAL
                    elif amount > LARGE_TRANSACTION_THRESHOLD or rule_code == "PEP_TRANSACTION":
                        severity = AlertSeverity.HIGH
                    else:
                        severity = AlertSeverity.MEDIUM
                    tpl = render_aml(
                        rule_code,
                        amount=amount,
                        currency="USD",
                        country=cp_country,
                        threshold=LARGE_TRANSACTION_THRESHOLD,
                    )
                    alert = AMLAlert(
                        client_id=profile.id,
                        transaction_id=txn.id,
                        alert_type=alert_type,
                        severity=severity,
                        status=random.choice([AlertStatus.OPEN, AlertStatus.UNDER_INVESTIGATION, AlertStatus.RESOLVED]),
                        title=tpl["title"],
                        description=f"{tpl['explanation']}\n\nRecommended action: {tpl['recommended_action']}",
                        triggered_rule=rule_code,
                        rule_parameters={"recommended_action": tpl["recommended_action"], "flag_reason": flag_reason},
                        amount_involved=amount,
                        is_auto_generated=True,
                        # Alerts fire shortly after the transaction (0-3 days), capped at now,
                        # so they inherit the transaction's 6-month distribution.
                        created_at=min(
                            datetime.utcnow(),
                            txn_dt + timedelta(days=random.randint(0, 3), seconds=random.randint(0, 86399)),
                        ),
                    )
                    db.add(alert)

            # Rapid in/out movement of funds — a burst of deposits + withdrawals
            # clustered within a 2-hour window (classic layering pattern).
            if rapid_mover:
                burst_start = random_datetime_between(
                    client_created, datetime.utcnow() - timedelta(hours=RAPID_MOVEMENT_HOURS))
                burst_types = [
                    TransactionType.DEPOSIT, TransactionType.WITHDRAWAL,
                    TransactionType.TRANSFER, TransactionType.WITHDRAWAL,
                    TransactionType.PAYMENT, TransactionType.WITHDRAWAL,
                ][:RAPID_MOVEMENT_COUNT]
                step = timedelta(minutes=(RAPID_MOVEMENT_HOURS * 60) // (RAPID_MOVEMENT_COUNT + 1))
                last_btxn = None
                rapid_reason = render_flag_reason(
                    "RAPID_MOVEMENT", count=len(burst_types), window_hours=RAPID_MOVEMENT_HOURS)
                for j, btype in enumerate(burst_types):
                    bt = burst_start + step * j
                    btxn = Transaction(
                        client_id=profile.id,
                        transaction_ref=f"TXN-{uuid.uuid4().hex[:12].upper()}",
                        type=btype,
                        status=TransactionStatus.FLAGGED,
                        amount=round(random.uniform(2000, 9000), 2),
                        currency="USD",
                        counterparty_name=fake.name(),
                        counterparty_country=random.choice(NATIONALITIES),
                        description="Rapid movement burst (demo)",
                        is_flagged=True,
                        flag_reason=rapid_reason,
                        risk_score=55.0,
                        device_id=stable_device,
                        ip_address=stable_ip,
                        transaction_date=bt,
                        created_at=bt,
                    )
                    db.add(btxn)
                    last_btxn = btxn
                await db.flush()

                tpl = render_aml(
                    "RAPID_MOVEMENT", count=len(burst_types), window_hours=RAPID_MOVEMENT_HOURS)
                db.add(AMLAlert(
                    client_id=profile.id,
                    transaction_id=last_btxn.id,
                    alert_type=AlertType.RAPID_MOVEMENT,
                    severity=AlertSeverity.HIGH,
                    status=random.choice([AlertStatus.OPEN, AlertStatus.UNDER_INVESTIGATION]),
                    title=tpl["title"],
                    description=f"{tpl['explanation']}\n\nRecommended action: {tpl['recommended_action']}",
                    triggered_rule="RAPID_MOVEMENT",
                    rule_parameters={"recommended_action": tpl["recommended_action"], "flag_reason": rapid_reason},
                    amount_involved=None,
                    is_auto_generated=True,
                    created_at=min(datetime.utcnow(), burst_start + timedelta(hours=RAPID_MOVEMENT_HOURS)),
                ))

        await db.commit()

        print("Seeding detection rules and incident tickets...")
        await seed_detection_rules(db)
        await seed_incidents(db, staff)
        await db.commit()

        print(f"Seed complete: {len(STAFF_USERS)} staff + 50 clients with profiles, documents, "
              f"transactions, and alerts (incl. sanctions, PEP and rapid-movement cases), "
              f"plus detection rules and incident tickets with risk assessments and "
              f"false-positive classifications.")


if __name__ == "__main__":
    asyncio.run(seed())
