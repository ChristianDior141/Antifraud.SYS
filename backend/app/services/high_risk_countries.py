"""
High-Risk Jurisdictions — single source of truth.

ISO-3166 alpha-2 codes for jurisdictions identified as high-risk for money
laundering / terrorist financing (FATF "call for action" & "increased
monitoring" lists, plus comprehensively sanctioned states). Both the risk
scoring engine and the AML monitor import this set so the two stay in sync.
"""
from typing import Optional

HIGH_RISK_COUNTRIES = frozenset({
    "AF",  # Afghanistan
    "BY",  # Belarus
    "CF",  # Central African Republic
    "CG",  # Congo (Republic)
    "CD",  # Congo (DRC)
    "CU",  # Cuba
    "ER",  # Eritrea
    "ET",  # Ethiopia
    "GN",  # Guinea
    "GW",  # Guinea-Bissau
    "HT",  # Haiti
    "IR",  # Iran
    "IQ",  # Iraq
    "KP",  # North Korea
    "LB",  # Lebanon
    "LY",  # Libya
    "ML",  # Mali
    "MM",  # Myanmar
    "NI",  # Nicaragua
    "RU",  # Russia
    "SO",  # Somalia
    "SS",  # South Sudan
    "SD",  # Sudan
    "SY",  # Syria
    "VE",  # Venezuela
    "YE",  # Yemen
    "ZW",  # Zimbabwe
})


def is_high_risk(country: Optional[str]) -> bool:
    """True if the given country (name or ISO-2 code) is high-risk.

    Accepts either a 2-letter code ("IR") or a longer string whose first two
    characters are the code; matching is case-insensitive.
    """
    code = (country or "")[:2].upper()
    return code in HIGH_RISK_COUNTRIES
