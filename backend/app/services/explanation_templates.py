"""
Explanation Templates
=====================
Central registry of ready-made, human-readable explanations the platform
uses to describe *why* something was flagged. Instead of scattering text
strings across the AML monitor, risk engine and seed script, every rule and
risk factor references a template here. The system picks the matching
template for the situation and fills in the context (amounts, counts,
countries, etc.).

Each template provides:
  - title:               short headline shown in lists / badges
  - explanation:         plain-language reason (the "why")
  - recommended_action:  suggested next step for the compliance officer

Use:
    from app.services.explanation_templates import render_aml, render_risk_factor

    tpl = render_aml("LARGE_TRANSACTION", amount=52000, currency="USD")
    tpl["title"], tpl["explanation"], tpl["recommended_action"]
"""
from typing import Dict, Any, List, Optional


# ---------------------------------------------------------------------------
# AML rule templates — keyed by triggered_rule code
# ---------------------------------------------------------------------------
AML_TEMPLATES: Dict[str, Dict[str, str]] = {
    "LARGE_TRANSACTION": {
        "title": "Large Transaction: ${amount:,.0f}",
        "explanation": (
            "A single transaction of ${amount:,.2f} {currency} exceeds the "
            "${threshold:,.0f} reporting threshold. Large one-off movements can "
            "indicate layering of illicit funds or undeclared income."
        ),
        "recommended_action": (
            "Verify the source of funds and confirm the transaction matches the "
            "client's expected activity profile before clearing."
        ),
    },
    "STRUCTURING_DETECTION": {
        "title": "Possible Structuring Detected",
        "explanation": (
            "{count} transactions between ${low:,.0f} and ${high:,.0f} were made "
            "within {window_hours} hours. Repeated amounts just below the "
            "${threshold:,.0f} reporting threshold suggest deliberate structuring "
            "(smurfing) to avoid detection."
        ),
        "recommended_action": (
            "Aggregate the related transactions, review the pattern, and consider "
            "filing a Suspicious Activity Report (SAR) if intent is confirmed."
        ),
    },
    "HIGH_RISK_JURISDICTION": {
        "title": "Transaction to High-Risk Country: {country}",
        "explanation": (
            "A transfer involving {country}, a jurisdiction identified as high-risk "
            "for money laundering or terrorist financing (FATF / sanctions lists). "
            "Cross-border flows to such regions require enhanced scrutiny."
        ),
        "recommended_action": (
            "Apply enhanced due diligence (EDD): confirm the counterparty, purpose "
            "of payment, and screen against sanctions lists."
        ),
    },
    "VELOCITY_CHECK": {
        "title": "High Transaction Frequency: {count} in {window_hours}h",
        "explanation": (
            "The client performed {count} transactions in the past {window_hours} "
            "hours, exceeding normal velocity. Bursts of activity can indicate "
            "account takeover or rapid movement of funds."
        ),
        "recommended_action": (
            "Review the session/device history for anomalies and confirm the "
            "activity was initiated by the genuine account holder."
        ),
    },
    "RAPID_MOVEMENT": {
        "title": "Rapid Movement of Funds",
        "explanation": (
            "{count} transfers occurred within {window_hours} hours, with funds "
            "entering and leaving the account quickly. Pass-through behaviour is a "
            "common layering technique."
        ),
        "recommended_action": (
            "Trace the inbound source and outbound destination to determine whether "
            "the account is being used as a conduit."
        ),
    },
    "PEP_TRANSACTION": {
        "title": "Transaction Involving a PEP",
        "explanation": (
            "This activity is linked to a Politically Exposed Person. PEPs carry a "
            "higher inherent risk of corruption and bribery, so their transactions "
            "warrant closer review."
        ),
        "recommended_action": (
            "Confirm senior management approval is on file and that the source of "
            "wealth has been independently verified."
        ),
    },
    "SANCTIONS_HIT": {
        "title": "Potential Sanctions Match",
        "explanation": (
            "The client or counterparty potentially matches an entry on a sanctions "
            "list. Processing sanctioned transactions is a serious regulatory breach."
        ),
        "recommended_action": (
            "Freeze the transaction immediately, confirm the match, and escalate to "
            "the compliance lead for mandatory reporting."
        ),
    },
    "AUTO_DETECTION": {
        "title": "Suspicious Activity Detected",
        "explanation": (
            "An automated monitoring rule flagged this transaction of "
            "${amount:,.0f} for review based on the client's risk profile and "
            "transaction characteristics."
        ),
        "recommended_action": (
            "Review the transaction details and the client's history to determine "
            "whether the alert is a true positive."
        ),
    },
}


# ---------------------------------------------------------------------------
# Transaction flag-reason templates — concise, used on the transaction row
# ---------------------------------------------------------------------------
FLAG_REASON_TEMPLATES: Dict[str, str] = {
    "LARGE_TRANSACTION": "Large transaction (${amount:,.0f} exceeds ${threshold:,.0f} threshold)",
    "HIGH_RISK_JURISDICTION": "Counterparty in high-risk jurisdiction ({country})",
    "STRUCTURING_DETECTION": "Possible structuring — repeated amounts below ${threshold:,.0f}",
    "VELOCITY_CHECK": "Unusually high transaction frequency ({count} in {window_hours}h)",
    "RAPID_MOVEMENT": "Rapid in-and-out movement of funds",
    "ELEVATED_RISK_PROFILE": "Client has an elevated risk profile",
    "PEP_TRANSACTION": "Transaction linked to a Politically Exposed Person",
    "SANCTIONS_HIT": "Potential sanctions list match",
    "GENERIC": "Flagged by automated AML rules",
}


# ---------------------------------------------------------------------------
# Risk-factor explanation templates — keyed by factor code
# ---------------------------------------------------------------------------
RISK_FACTOR_TEMPLATES: Dict[str, Dict[str, str]] = {
    "PEP": {
        "factor": "PEP Status",
        "explanation": "Client is a Politically Exposed Person, which raises the inherent risk of corruption-related activity.",
        "recommended_action": "Obtain senior management sign-off and verify source of wealth.",
    },
    "SANCTIONS": {
        "factor": "Sanctions Hit",
        "explanation": "Client appears on, or closely matches, a sanctions list.",
        "recommended_action": "Halt onboarding and escalate for mandatory screening review.",
    },
    "HIGH_RISK_COUNTRY": {
        "factor": "High-Risk Country ({label})",
        "explanation": "The client's {label} country is on the high-risk jurisdiction list for money laundering / terrorist financing.",
        "recommended_action": "Apply enhanced due diligence and document the rationale for the relationship.",
    },
    "INCOMPLETE_PROFILE": {
        "factor": "Incomplete Profile",
        "explanation": "Required KYC fields are missing: {missing}. Incomplete data prevents proper risk assessment.",
        "recommended_action": "Request the missing information from the client before approval.",
    },
    "HIGH_VOLUME": {
        "factor": "High Total Volume",
        "explanation": "Total transaction volume of ${total_amount:,.0f} exceeds the expected threshold for this profile.",
        "recommended_action": "Confirm the volume is consistent with the declared source of funds.",
    },
    "LARGE_TXNS": {
        "factor": "Large Transactions",
        "explanation": "{count} transactions over $10,000 were observed, increasing exposure to large-value laundering.",
        "recommended_action": "Sample-review the largest transactions and verify supporting documentation.",
    },
    "HIGH_FREQUENCY": {
        "factor": "High Frequency",
        "explanation": "{count} transactions occurred within 24 hours, exceeding normal activity levels.",
        "recommended_action": "Check for automated/scripted activity or account compromise.",
    },
    "FLAGGED_TXNS": {
        "factor": "Flagged Transactions",
        "explanation": "{count} of the client's transactions were previously flagged by AML rules.",
        "recommended_action": "Review the open alerts and resolve them before changing the client's status.",
    },
    "NO_DOCUMENTS": {
        "factor": "No Documents",
        "explanation": "No identity or address documents have been uploaded, so identity cannot be verified.",
        "recommended_action": "Request and verify the mandatory KYC documents.",
    },
    "REJECTED_DOCUMENTS": {
        "factor": "Rejected Documents",
        "explanation": "{count} document(s) were rejected, indicating possible forgery or poor-quality submissions.",
        "recommended_action": "Request fresh, valid documents and re-run verification.",
    },
    "VOLUME_DEVIATION": {
        "factor": "Volume Deviation",
        "explanation": "Recent 30-day activity of ${actual:,.0f} far exceeds the client's declared expected monthly volume of ${expected:,.0f}.",
        "recommended_action": "Confirm the change in activity with the client and update the expected profile or escalate.",
    },
    "MULTIPLE_DEVICES": {
        "factor": "Multiple Devices",
        "explanation": "Transactions were initiated from {count} distinct devices, which can indicate account sharing or takeover.",
        "recommended_action": "Verify the devices belong to the genuine account holder and review for compromise.",
    },
    "MULTIPLE_IPS": {
        "factor": "Multiple IP Addresses",
        "explanation": "Activity originated from {count} distinct IP addresses, an unusual spread for a single account.",
        "recommended_action": "Check the locations/networks for anomalies and confirm the activity is legitimate.",
    },
    "UNEXPECTED_TXN_TYPE": {
        "factor": "Undeclared Transaction Types",
        "explanation": "The client used transaction types they did not declare during onboarding: {types}.",
        "recommended_action": "Reconcile actual usage with the declared profile and update KYC if appropriate.",
    },
}


def _safe_format(template: str, context: Dict[str, Any]) -> str:
    """Format a template, leaving the raw string if a key is missing."""
    try:
        return template.format(**context)
    except (KeyError, IndexError, ValueError):
        return template


def render_aml(rule_code: str, **context: Any) -> Dict[str, str]:
    """Return {title, explanation, recommended_action} for an AML rule."""
    tpl = AML_TEMPLATES.get(rule_code, AML_TEMPLATES["AUTO_DETECTION"])
    return {
        "title": _safe_format(tpl["title"], context),
        "explanation": _safe_format(tpl["explanation"], context),
        "recommended_action": _safe_format(tpl["recommended_action"], context),
    }


def render_flag_reason(rule_code: str, **context: Any) -> str:
    """Return a concise one-line flag reason for a transaction row."""
    tpl = FLAG_REASON_TEMPLATES.get(rule_code, FLAG_REASON_TEMPLATES["GENERIC"])
    return _safe_format(tpl, context)


def combine_flag_reasons(reasons: List[str]) -> str:
    """Join multiple concise reasons into one string."""
    return "; ".join(r for r in reasons if r) or FLAG_REASON_TEMPLATES["GENERIC"]


def render_risk_factor(factor_code: str, score: float, **context: Any) -> Dict[str, Any]:
    """Return a risk-factor dict enriched with explanation + recommended action."""
    tpl = RISK_FACTOR_TEMPLATES.get(factor_code)
    if not tpl:
        return {"factor": factor_code, "score": score, "description": "", "recommended_action": ""}
    return {
        "factor": _safe_format(tpl["factor"], context),
        "score": score,
        "description": _safe_format(tpl["explanation"], context),
        "recommended_action": _safe_format(tpl["recommended_action"], context),
    }
