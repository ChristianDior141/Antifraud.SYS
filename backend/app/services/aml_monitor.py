"""
AML Monitoring Engine — evaluates transactions against rule-based patterns
and generates alerts when suspicious activity is detected.
"""
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sqlfunc
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.aml import AMLAlert, AlertType, AlertSeverity, AlertStatus
from app.models.client import ClientProfile
from app.services.explanation_templates import render_aml, render_flag_reason, combine_flag_reasons
from app.services.high_risk_countries import is_high_risk


def _build_alert(
    *, client_id: int, transaction_id: int, alert_type: AlertType,
    severity: AlertSeverity, rule_code: str, flag_reason: str,
    amount_involved: Optional[float] = None, countries_involved: Optional[list] = None,
    **context,
) -> AMLAlert:
    """Construct an AMLAlert with text pulled from the explanation templates."""
    tpl = render_aml(rule_code, **context)
    return AMLAlert(
        client_id=client_id,
        transaction_id=transaction_id,
        alert_type=alert_type,
        severity=severity,
        status=AlertStatus.OPEN,
        title=tpl["title"],
        description=f"{tpl['explanation']}\n\nRecommended action: {tpl['recommended_action']}",
        triggered_rule=rule_code,
        rule_parameters={
            "recommended_action": tpl["recommended_action"],
            "flag_reason": flag_reason,
            **context,
        },
        amount_involved=amount_involved,
        countries_involved=countries_involved,
        is_auto_generated=True,
    )


STRUCTURING_THRESHOLD = 10_000
LARGE_TRANSACTION_THRESHOLD = 50_000
HIGH_FREQUENCY_COUNT = 10
HIGH_FREQUENCY_WINDOW_HOURS = 24
RAPID_MOVEMENT_HOURS = 2
RAPID_MOVEMENT_COUNT = 5
PEP_MATERIALITY_THRESHOLD = 10_000  # only alert on PEP movements above this
OUTFLOW_TYPES = (TransactionType.WITHDRAWAL, TransactionType.TRANSFER, TransactionType.PAYMENT)


async def _check_structuring(
    client: ClientProfile, transaction: Transaction, db: AsyncSession
) -> Optional[AMLAlert]:
    """Detect potential structuring (multiple transactions just below reporting threshold)."""
    window_start = datetime.utcnow() - timedelta(hours=24)
    result = await db.execute(
        select(Transaction).where(
            Transaction.client_id == client.id,
            Transaction.amount.between(STRUCTURING_THRESHOLD * 0.8, STRUCTURING_THRESHOLD),
            Transaction.transaction_date >= window_start,
        )
    )
    suspects = result.scalars().all()
    if len(suspects) >= 3:
        rule = "STRUCTURING_DETECTION"
        ctx = {
            "count": len(suspects),
            "low": STRUCTURING_THRESHOLD * 0.8,
            "high": STRUCTURING_THRESHOLD,
            "threshold": STRUCTURING_THRESHOLD,
            "window_hours": 24,
        }
        return _build_alert(
            client_id=client.id,
            transaction_id=transaction.id,
            alert_type=AlertType.STRUCTURING,
            severity=AlertSeverity.HIGH,
            rule_code=rule,
            flag_reason=render_flag_reason(rule, **ctx),
            amount_involved=sum(t.amount for t in suspects),
            **ctx,
        )
    return None


async def _check_large_transaction(
    client: ClientProfile, transaction: Transaction
) -> Optional[AMLAlert]:
    if transaction.amount >= LARGE_TRANSACTION_THRESHOLD:
        severity = AlertSeverity.CRITICAL if transaction.amount >= 100_000 else AlertSeverity.HIGH
        rule = "LARGE_TRANSACTION"
        ctx = {
            "amount": transaction.amount,
            "currency": transaction.currency,
            "threshold": LARGE_TRANSACTION_THRESHOLD,
        }
        return _build_alert(
            client_id=client.id,
            transaction_id=transaction.id,
            alert_type=AlertType.LARGE_CASH,
            severity=severity,
            rule_code=rule,
            flag_reason=render_flag_reason(rule, **ctx),
            amount_involved=transaction.amount,
            **ctx,
        )
    return None


async def _check_high_risk_jurisdiction(
    client: ClientProfile, transaction: Transaction
) -> Optional[AMLAlert]:
    if is_high_risk(transaction.counterparty_country):
        rule = "HIGH_RISK_JURISDICTION"
        ctx = {"country": transaction.counterparty_country}
        return _build_alert(
            client_id=client.id,
            transaction_id=transaction.id,
            alert_type=AlertType.HIGH_RISK_JURISDICTION,
            severity=AlertSeverity.HIGH,
            rule_code=rule,
            flag_reason=render_flag_reason(rule, **ctx),
            amount_involved=transaction.amount,
            countries_involved=[transaction.counterparty_country],
            **ctx,
        )
    return None


async def _check_velocity(
    client: ClientProfile, transaction: Transaction, db: AsyncSession
) -> Optional[AMLAlert]:
    window_start = datetime.utcnow() - timedelta(hours=HIGH_FREQUENCY_WINDOW_HOURS)
    result = await db.execute(
        select(sqlfunc.count(Transaction.id)).where(
            Transaction.client_id == client.id,
            Transaction.transaction_date >= window_start,
        )
    )
    count = result.scalar()
    if count > HIGH_FREQUENCY_COUNT:
        rule = "VELOCITY_CHECK"
        ctx = {"count": count, "window_hours": HIGH_FREQUENCY_WINDOW_HOURS}
        return _build_alert(
            client_id=client.id,
            transaction_id=transaction.id,
            alert_type=AlertType.VELOCITY_CHECK,
            severity=AlertSeverity.MEDIUM,
            rule_code=rule,
            flag_reason=render_flag_reason(rule, **ctx),
            amount_involved=transaction.amount,
            **ctx,
        )
    return None


async def _check_rapid_movement(
    client: ClientProfile, transaction: Transaction, db: AsyncSession
) -> Optional[AMLAlert]:
    """Detect funds entering and leaving the account in quick succession (layering)."""
    window_start = datetime.utcnow() - timedelta(hours=RAPID_MOVEMENT_HOURS)
    result = await db.execute(
        select(Transaction).where(
            Transaction.client_id == client.id,
            Transaction.transaction_date >= window_start,
        )
    )
    recent = result.scalars().all()
    has_inflow = any(t.type == TransactionType.DEPOSIT for t in recent)
    has_outflow = any(t.type in OUTFLOW_TYPES for t in recent)
    if len(recent) >= RAPID_MOVEMENT_COUNT and has_inflow and has_outflow:
        rule = "RAPID_MOVEMENT"
        ctx = {"count": len(recent), "window_hours": RAPID_MOVEMENT_HOURS}
        return _build_alert(
            client_id=client.id,
            transaction_id=transaction.id,
            alert_type=AlertType.RAPID_MOVEMENT,
            severity=AlertSeverity.HIGH,
            rule_code=rule,
            flag_reason=render_flag_reason(rule, **ctx),
            amount_involved=sum(t.amount for t in recent),
            **ctx,
        )
    return None


async def _check_pep(
    client: ClientProfile, transaction: Transaction
) -> Optional[AMLAlert]:
    """Flag material transactions linked to a Politically Exposed Person."""
    if client.is_pep and transaction.amount >= PEP_MATERIALITY_THRESHOLD:
        rule = "PEP_TRANSACTION"
        ctx = {"amount": transaction.amount}
        return _build_alert(
            client_id=client.id,
            transaction_id=transaction.id,
            alert_type=AlertType.PEP_TRANSACTION,
            severity=AlertSeverity.HIGH,
            rule_code=rule,
            flag_reason=render_flag_reason(rule, **ctx),
            amount_involved=transaction.amount,
            **ctx,
        )
    return None


async def _check_sanctions(
    client: ClientProfile, transaction: Transaction
) -> Optional[AMLAlert]:
    """Any movement by a sanctioned party is a critical regulatory breach."""
    if client.is_sanctioned:
        rule = "SANCTIONS_HIT"
        return _build_alert(
            client_id=client.id,
            transaction_id=transaction.id,
            alert_type=AlertType.SANCTIONS_HIT,
            severity=AlertSeverity.CRITICAL,
            rule_code=rule,
            flag_reason=render_flag_reason(rule),
            amount_involved=transaction.amount,
        )
    return None


async def evaluate_transaction(
    client: ClientProfile, transaction: Transaction, db: AsyncSession
) -> List[AMLAlert]:
    alerts: List[AMLAlert] = []

    # Run sequentially: several checks query the DB and an AsyncSession does
    # not support concurrent operations on the same connection.
    checks = [
        await _check_structuring(client, transaction, db),
        await _check_large_transaction(client, transaction),
        await _check_high_risk_jurisdiction(client, transaction),
        await _check_velocity(client, transaction, db),
        await _check_rapid_movement(client, transaction, db),
        await _check_pep(client, transaction),
        await _check_sanctions(client, transaction),
    ]

    for alert in checks:
        if alert:
            db.add(alert)
            alerts.append(alert)

    if alerts:
        transaction.is_flagged = True
        # Concise, template-driven flag reasons stored per alert in rule_parameters
        reasons = [
            (a.rule_parameters or {}).get("flag_reason", a.title) for a in alerts
        ]
        transaction.flag_reason = combine_flag_reasons(reasons)
        transaction.status = TransactionStatus.FLAGGED
        db.add(transaction)
        await db.flush()

    return alerts
