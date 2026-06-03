"""Tests for the risk scoring engine."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.risk_engine import (
    _score_personal, _score_geographic, _determine_risk_level, WEIGHTS
)
from app.models.client import ClientProfile, RiskLevel


def make_client(**kwargs) -> ClientProfile:
    defaults = {
        "id": 1, "user_id": 1,
        "first_name": "John", "last_name": "Doe",
        "nationality": "US", "country_of_residence": "US",
        "is_pep": False, "is_sanctioned": False, "is_high_risk_country": False,
        "date_of_birth": "1990-01-01", "phone_number": "555-0000",
        "occupation": "Engineer", "source_of_funds": "salary",
        "documents": [],
    }
    defaults.update(kwargs)
    client = MagicMock(spec=ClientProfile)
    for k, v in defaults.items():
        setattr(client, k, v)
    return client


def test_determine_risk_level():
    assert _determine_risk_level(10) == "low"
    assert _determine_risk_level(30) == "low"
    assert _determine_risk_level(31) == "medium"
    assert _determine_risk_level(60) == "medium"
    assert _determine_risk_level(61) == "high"
    assert _determine_risk_level(80) == "high"
    assert _determine_risk_level(81) == "critical"
    assert _determine_risk_level(100) == "critical"


def test_personal_score_clean_client():
    client = make_client()
    score, factors = _score_personal(client)
    assert score == 0.0
    assert factors == []


def test_personal_score_pep():
    client = make_client(is_pep=True)
    score, factors = _score_personal(client)
    assert score == 40.0
    assert any("PEP" in f["factor"] for f in factors)


def test_personal_score_sanctioned():
    client = make_client(is_sanctioned=True)
    score, factors = _score_personal(client)
    assert score == 50.0


def test_personal_score_pep_and_sanctioned():
    client = make_client(is_pep=True, is_sanctioned=True)
    score, _ = _score_personal(client)
    assert score == min(90.0, 100)


def test_personal_score_missing_fields():
    client = make_client(date_of_birth=None, phone_number=None)
    score, factors = _score_personal(client)
    assert score > 0
    assert any("Incomplete" in f["factor"] for f in factors)


def test_geographic_score_low_risk():
    client = make_client(nationality="US", country_of_residence="US", country="US")
    score, factors = _score_geographic(client)
    assert score == 0.0


def test_geographic_score_high_risk_nationality():
    client = make_client(nationality="IR", country_of_residence="US", country="US")
    score, factors = _score_geographic(client)
    assert score > 0
    assert any("High-Risk" in f["factor"] for f in factors)


def test_weights_sum_to_one():
    total = sum(WEIGHTS.values())
    assert abs(total - 1.0) < 0.001
