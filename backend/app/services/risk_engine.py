"""
Risk Scoring Engine — calculates a composite 0-100 risk score for a client
based on personal, geographic, transactional, and behavioral factors.
"""
from typing import Dict, List, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sqlfunc
from datetime import datetime, timedelta
from app.models.client import ClientProfile, RiskLevel
from app.models.transaction import Transaction, TransactionStatus
from app.models.risk import RiskScore
from app.services.explanation_templates import render_risk_factor
from app.services.high_risk_countries import is_high_risk

WEIGHTS = {
    "personal": 0.30,
    "geographic": 0.25,
    "transaction": 0.25,
    "behavioral": 0.10,
    "document": 0.10,
}


def _determine_risk_level(score: float) -> str:
    if score <= 30:
        return "low"
    if score <= 60:
        return "medium"
    if score <= 80:
        return "high"
    return "critical"


def _score_personal(client: ClientProfile) -> Tuple[float, List[Dict]]:
    score = 0.0
    factors: List[Dict] = []

    if client.is_pep:
        score += 40
        factors.append(render_risk_factor("PEP", 40))

    if client.is_sanctioned:
        score += 50
        factors.append(render_risk_factor("SANCTIONS", 50))

    missing = []
    for field in ["date_of_birth", "nationality", "occupation", "source_of_funds", "phone_number"]:
        if not getattr(client, field):
            missing.append(field)
    if missing:
        penalty = min(len(missing) * 4, 20)
        score += penalty
        factors.append(render_risk_factor("INCOMPLETE_PROFILE", penalty, missing=", ".join(missing)))

    return min(score, 100), factors


def _score_geographic(client: ClientProfile) -> Tuple[float, List[Dict]]:
    score = 0.0
    factors: List[Dict] = []

    nationality = client.nationality
    residence = client.country_of_residence or client.country

    for value, label in [(nationality, "nationality"), (residence, "residence")]:
        if is_high_risk(value):
            score += 35
            factors.append(render_risk_factor("HIGH_RISK_COUNTRY", 35, label=label))

    return min(score, 100), factors


def _score_transactions(client: ClientProfile, transactions: List[Transaction]) -> Tuple[float, List[Dict]]:
    score = 0.0
    factors: List[Dict] = []

    if not transactions:
        return 0.0, []

    total_amount = sum(t.amount for t in transactions)
    if total_amount > 100_000:
        score += 20
        factors.append(render_risk_factor("HIGH_VOLUME", 20, total_amount=total_amount))

    large_txns = [t for t in transactions if t.amount > 10_000]
    if large_txns:
        s = min(len(large_txns) * 5, 20)
        score += s
        factors.append(render_risk_factor("LARGE_TXNS", s, count=len(large_txns)))

    now = datetime.utcnow()
    window_24h = [t for t in transactions if t.transaction_date and
                  (now - t.transaction_date.replace(tzinfo=None)).total_seconds() < 86400]
    if len(window_24h) > 10:
        score += 25
        factors.append(render_risk_factor("HIGH_FREQUENCY", 25, count=len(window_24h)))

    flagged = [t for t in transactions if t.is_flagged]
    if flagged:
        s = min(len(flagged) * 10, 30)
        score += s
        factors.append(render_risk_factor("FLAGGED_TXNS", s, count=len(flagged)))

    return min(score, 100), factors


def _score_behavioral(client: ClientProfile, transactions: List[Transaction]) -> Tuple[float, List[Dict]]:
    """Behavioural signals derived from how the client actually transacts:
    volume vs. declared expectation, device/IP spread, and undeclared
    transaction types. These complement the raw transaction-amount checks.
    """
    score = 0.0
    factors: List[Dict] = []

    if not transactions:
        return 0.0, []

    now = datetime.utcnow()

    # 1. Activity far above the client's declared expected monthly volume
    expected = client.expected_monthly_transaction_volume
    if expected and expected > 0:
        recent = [
            t for t in transactions
            if t.transaction_date
            and (now - t.transaction_date.replace(tzinfo=None)) <= timedelta(days=30)
        ]
        actual = sum(t.amount for t in recent)
        if actual > expected * 3:
            score += 20
            factors.append(render_risk_factor(
                "VOLUME_DEVIATION", 20, actual=actual, expected=expected))

    # 2. Many distinct devices — possible account sharing / takeover
    devices = {t.device_id for t in transactions if t.device_id}
    if len(devices) > 3:
        score += 15
        factors.append(render_risk_factor("MULTIPLE_DEVICES", 15, count=len(devices)))

    # 3. Many distinct IP addresses
    ips = {t.ip_address for t in transactions if t.ip_address}
    if len(ips) > 5:
        score += 15
        factors.append(render_risk_factor("MULTIPLE_IPS", 15, count=len(ips)))

    # 4. Transaction types the client never declared they would use
    expected_types = client.expected_transaction_types
    if expected_types:
        declared = {str(t).lower() for t in expected_types}
        used = {
            (t.type.value if hasattr(t.type, "value") else str(t.type)).lower()
            for t in transactions
        }
        undeclared = used - declared
        if undeclared:
            score += 10
            factors.append(render_risk_factor(
                "UNEXPECTED_TXN_TYPE", 10, types=", ".join(sorted(undeclared))))

    return min(score, 100), factors


async def _score_documents(client: ClientProfile, db: AsyncSession) -> Tuple[float, List[Dict]]:
    score = 0.0
    factors: List[Dict] = []

    from app.models.document import Document, DocumentStatus
    result = await db.execute(
        select(Document).where(Document.client_id == client.id)
    )
    documents = result.scalars().all()

    if not documents:
        score += 30
        factors.append(render_risk_factor("NO_DOCUMENTS", 30))
        return score, factors

    rejected = [d for d in documents if d.status == DocumentStatus.REJECTED]
    if rejected:
        s = min(len(rejected) * 15, 30)
        score += s
        factors.append(render_risk_factor("REJECTED_DOCUMENTS", s, count=len(rejected)))

    return min(score, 100), factors


async def calculate_risk_score(client: ClientProfile, db: AsyncSession) -> RiskScore:
    result = await db.execute(
        select(Transaction).where(Transaction.client_id == client.id)
    )
    transactions = result.scalars().all()

    personal_score, personal_factors = _score_personal(client)
    geo_score, geo_factors = _score_geographic(client)
    txn_score, txn_factors = _score_transactions(client, transactions)
    behavioral_score, beh_factors = _score_behavioral(client, transactions)
    doc_score, doc_factors = await _score_documents(client, db)

    total = (
        personal_score * WEIGHTS["personal"]
        + geo_score * WEIGHTS["geographic"]
        + txn_score * WEIGHTS["transaction"]
        + behavioral_score * WEIGHTS["behavioral"]
        + doc_score * WEIGHTS["document"]
    )

    all_factors = personal_factors + geo_factors + txn_factors + beh_factors + doc_factors

    risk_record = RiskScore(
        client_id=client.id,
        total_score=round(total, 2),
        risk_level=_determine_risk_level(total),
        personal_risk_score=round(personal_score, 2),
        transaction_risk_score=round(txn_score, 2),
        behavioral_risk_score=round(behavioral_score, 2),
        geographic_risk_score=round(geo_score, 2),
        document_risk_score=round(doc_score, 2),
        risk_factors={"factors": all_factors},
        pep_flag=client.is_pep,
        sanctions_flag=client.is_sanctioned,
        high_risk_country_flag=client.is_high_risk_country,
        unusual_transaction_flag=any("Flagged" in f.get("factor", "") for f in txn_factors),
        calculated_by="system",
    )

    db.add(risk_record)

    # Update denormalized fields on the client
    client.risk_score = round(total, 2)
    from app.models.client import RiskLevel
    client.risk_level = RiskLevel(risk_record.risk_level)
    db.add(client)

    await db.flush()
    return risk_record
