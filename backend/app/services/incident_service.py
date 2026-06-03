"""
Incident service — bridges AML alerts to incident tickets and computes
detection-rule effectiveness from investigation outcomes.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aml import AMLAlert, AlertSeverity
from app.models.client import RiskLevel
from app.models.detection_rule import DetectionRule
from app.models.incident import (
    IncidentTicket, IncidentClassification, TicketPriority, TicketStatus, FalsePositive,
)


# Canonical detection-rule registry — mirrors the AML monitor / risk engine.
RULE_REGISTRY: List[Dict[str, Any]] = [
    {"rule_code": "STRUCTURING_DETECTION", "name": "Structuring Detection",
     "alert_type": "structuring",
     "description": "Multiple transactions just below the reporting threshold within a short window.",
     "parameters": {"min_count": 3, "low": 8000, "high": 10000, "window_hours": 24}},
    {"rule_code": "LARGE_TRANSACTION", "name": "Large Transaction",
     "alert_type": "large_cash",
     "description": "A single transaction at or above the reporting threshold.",
     "parameters": {"threshold": 50000, "critical_threshold": 100000}},
    {"rule_code": "HIGH_RISK_JURISDICTION", "name": "High-Risk Jurisdiction",
     "alert_type": "high_risk_jurisdiction",
     "description": "Counterparty located in a high-risk jurisdiction.",
     "parameters": {"window_hours": None}},
    {"rule_code": "VELOCITY_CHECK", "name": "Velocity Check",
     "alert_type": "velocity_check",
     "description": "Unusually high transaction frequency for the client.",
     "parameters": {"count": 10, "window_hours": 24}},
    {"rule_code": "RAPID_MOVEMENT", "name": "Rapid Movement of Funds",
     "alert_type": "rapid_movement",
     "description": "Funds entering and leaving the account in quick succession (layering).",
     "parameters": {"count": 5, "window_hours": 2}},
    {"rule_code": "PEP_TRANSACTION", "name": "PEP Transaction",
     "alert_type": "pep_transaction",
     "description": "Material transaction linked to a Politically Exposed Person.",
     "parameters": {"materiality_threshold": 10000}},
    {"rule_code": "SANCTIONS_HIT", "name": "Sanctions Hit",
     "alert_type": "sanctions_hit",
     "description": "Any transaction by a sanctioned party.",
     "parameters": {}},
]

_SEVERITY_TO_PRIORITY = {
    AlertSeverity.LOW: TicketPriority.LOW,
    AlertSeverity.MEDIUM: TicketPriority.MEDIUM,
    AlertSeverity.HIGH: TicketPriority.HIGH,
    AlertSeverity.CRITICAL: TicketPriority.CRITICAL,
}

_SEVERITY_TO_RISK = {
    AlertSeverity.LOW: RiskLevel.LOW,
    AlertSeverity.MEDIUM: RiskLevel.MEDIUM,
    AlertSeverity.HIGH: RiskLevel.HIGH,
    AlertSeverity.CRITICAL: RiskLevel.CRITICAL,
}


def derive_priority(severity: AlertSeverity) -> TicketPriority:
    return _SEVERITY_TO_PRIORITY.get(severity, TicketPriority.MEDIUM)


def derive_risk_level(severity: AlertSeverity) -> RiskLevel:
    return _SEVERITY_TO_RISK.get(severity, RiskLevel.MEDIUM)


async def get_rule_by_code(rule_code: Optional[str], db: AsyncSession) -> Optional[DetectionRule]:
    if not rule_code:
        return None
    result = await db.execute(select(DetectionRule).where(DetectionRule.rule_code == rule_code))
    return result.scalar_one_or_none()


async def create_ticket_for_alert(alert: AMLAlert, db: AsyncSession) -> Optional[IncidentTicket]:
    """Create an incident ticket for an alert. Idempotent — returns the existing
    ticket if one is already linked to the alert."""
    existing = await db.execute(
        select(IncidentTicket).where(IncidentTicket.alert_id == alert.id)
    )
    found = existing.scalar_one_or_none()
    if found:
        return found

    rule = await get_rule_by_code(alert.triggered_rule, db)
    ticket = IncidentTicket(
        alert_id=alert.id,
        client_id=alert.client_id,
        detection_rule_id=rule.id if rule else None,
        alert_source="AML Monitor",
        alert_type=alert.alert_type.value if hasattr(alert.alert_type, "value") else str(alert.alert_type),
        priority=derive_priority(alert.severity),
        risk_level=derive_risk_level(alert.severity),
        status=TicketStatus.NEW,
    )
    db.add(ticket)
    await db.flush()
    return ticket


async def compute_rule_stats(rule: DetectionRule, db: AsyncSession) -> Dict[str, float]:
    """Effectiveness scoring for a detection rule, derived from ticket outcomes."""
    total = await db.execute(
        select(func.count(IncidentTicket.id)).where(IncidentTicket.detection_rule_id == rule.id)
    )
    confirmed = await db.execute(
        select(func.count(IncidentTicket.id)).where(
            IncidentTicket.detection_rule_id == rule.id,
            IncidentTicket.classification == IncidentClassification.REAL_INCIDENT,
        )
    )
    fp = await db.execute(
        select(func.count(FalsePositive.id)).where(FalsePositive.detection_rule_id == rule.id)
    )
    total_alerts = total.scalar() or 0
    confirmed_incidents = confirmed.scalar() or 0
    false_positives = fp.scalar() or 0

    classified = confirmed_incidents + false_positives
    fp_rate = (false_positives / classified * 100) if classified > 0 else 0.0
    effectiveness = 100.0 - fp_rate
    return {
        "total_alerts": total_alerts,
        "confirmed_incidents": confirmed_incidents,
        "false_positives": false_positives,
        "false_positive_rate": round(fp_rate, 1),
        "effectiveness_score": round(effectiveness, 1),
    }


def suggest_improvements(stats: Dict[str, float], fp_reasons: List[str]) -> List[str]:
    """Heuristic tuning suggestions based on FP rate and the reasons recorded."""
    tips: List[str] = []
    rate = stats.get("false_positive_rate", 0)
    if rate >= 50:
        tips.append("False-positive rate is very high — review this rule's thresholds urgently.")
    elif rate >= 25:
        tips.append("Elevated false-positive rate — consider tightening thresholds or adding context.")

    reason_set = set(fp_reasons)
    if "threshold_too_sensitive" in reason_set:
        tips.append("Raise the amount/count threshold; analysts report it is too sensitive.")
    if "legitimate_user_behavior" in reason_set or "whitelisted_activity" in reason_set:
        tips.append("Add a whitelist / expected-behaviour exception to reduce noise.")
    if "data_quality_issue" in reason_set:
        tips.append("Investigate upstream data quality feeding this rule.")
    if "incorrect_correlation_rule" in reason_set:
        tips.append("Re-examine the correlation logic — it is mis-firing.")
    if "configuration_error" in reason_set:
        tips.append("Audit the rule configuration for misconfiguration.")
    if not tips:
        tips.append("Rule is performing well; no tuning required.")
    return tips
