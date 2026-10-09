"""Tests for Phase 8: Weighted Risk Scoring Engine and Explainability Artifacts."""

import pytest
from fastapi.testclient import TestClient

from app.risk.engine import RiskEngine, score_to_severity


def test_score_to_severity_bands() -> None:
    """Validate severity band boundary mappings:

    0–30: LOW, 31–60: MEDIUM, 61–80: HIGH, 81–100: CRITICAL.
    """
    assert score_to_severity(0) == "LOW"
    assert score_to_severity(30) == "LOW"
    assert score_to_severity(31) == "MEDIUM"
    assert score_to_severity(60) == "MEDIUM"
    assert score_to_severity(61) == "HIGH"
    assert score_to_severity(80) == "HIGH"
    assert score_to_severity(81) == "CRITICAL"
    assert score_to_severity(94) == "CRITICAL"
    assert score_to_severity(100) == "CRITICAL"


def test_compute_composite_score_formula() -> None:
    """Test risk calculation: 30% rule, 30% ml, 25% correlation, 15% behavioral."""
    engine = RiskEngine(
        weight_rule=0.30,
        weight_ml=0.30,
        weight_correlation=0.25,
        weight_behavioral=0.15,
    )

    # 1. Baseline low scores
    score, severity, breakdown = engine.compute_composite_score(
        rule_score=20,
        ml_score=20,
        correlation_score=20,
        behavioral_score=20,
    )
    assert score == 20
    assert severity == "LOW"
    assert breakdown["contributions"]["rule"] == 6.0
    assert breakdown["contributions"]["ml"] == 6.0
    assert breakdown["contributions"]["correlation"] == 5.0
    assert breakdown["contributions"]["behavioral"] == 3.0

    # 2. Scenario F values: rule=95, ml=90, corr=100, beh=90
    # 0.30*95 + 0.30*90 + 0.25*100 + 0.15*90 = 28.5 + 27.0 + 25.0 + 13.5 = 94.0
    score_f, sev_f, bdown_f = engine.compute_composite_score(
        rule_score=95,
        ml_score=90,
        correlation_score=100,
        behavioral_score=90,
    )
    assert score_f == 94
    assert sev_f == "CRITICAL"
    assert bdown_f["contributions"]["rule"] == 28.5
    assert bdown_f["contributions"]["ml"] == 27.0
    assert bdown_f["contributions"]["correlation"] == 25.0
    assert bdown_f["contributions"]["behavioral"] == 13.5


def test_composite_score_bounds_clamping() -> None:
    """Scores above 100 or below 0 are strictly clamped into 0–100 range."""
    engine = RiskEngine()
    score_max, _, _ = engine.compute_composite_score(150, 150, 150, 150)
    assert score_max == 100

    score_min, _, _ = engine.compute_composite_score(-50, -20, 0, 0)
    assert score_min == 0


def test_risk_weights_api(client: TestClient) -> None:
    """GET /api/risk/weights returns active weights and severity band documentation."""
    resp = client.get("/api/risk/weights")
    assert resp.status_code == 200
    data = resp.json()

    assert data["weights"]["rule"] == 0.30
    assert data["weights"]["ml"] == 0.30
    assert data["weights"]["correlation"] == 0.25
    assert data["weights"]["behavioral"] == 0.15
    assert data["severity_bands"]["CRITICAL"] == "81–100"
    assert data["severity_bands"]["HIGH"] == "61–80"
    assert "round" in data["formula"]


def test_risk_calculate_simulation_api(client: TestClient) -> None:
    """POST /api/risk/calculate simulates composite risk calculations and breakdowns."""
    payload = {
        "rule_score": 95,
        "ml_score": 90,
        "correlation_score": 100,
        "behavioral_score": 90,
    }
    resp = client.post("/api/risk/calculate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["composite_score"] == 94
    assert data["severity"] == "CRITICAL"
    assert "Risk Score: 94/100 (CRITICAL)" in data["display_label"]
    assert data["contributions"]["rule"] == 28.5
    assert data["contributions"]["ml"] == 27.0
    assert data["contributions"]["correlation"] == 25.0
    assert data["contributions"]["behavioral"] == 13.5


def test_risk_calculate_with_custom_weights(client: TestClient) -> None:
    """POST /api/risk/calculate supports custom weight experimentation."""
    payload = {
        "rule_score": 100,
        "ml_score": 50,
        "correlation_score": 50,
        "behavioral_score": 50,
        "custom_weights": {
            "rule": 0.50,
            "ml": 0.20,
            "correlation": 0.20,
            "behavioral": 0.10,
        },
    }
    resp = client.post("/api/risk/calculate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # 0.50*100 + 0.20*50 + 0.20*50 + 0.10*50 = 50 + 10 + 10 + 5 = 75
    assert data["composite_score"] == 75
    assert data["severity"] == "HIGH"


def test_risk_calculate_invalid_custom_weights(client: TestClient) -> None:
    """Custom weights that do not sum to ~1.0 return HTTP 422."""
    payload = {
        "rule_score": 80,
        "ml_score": 80,
        "correlation_score": 80,
        "behavioral_score": 80,
        "custom_weights": {
            "rule": 0.90,
            "ml": 0.90,
            "correlation": 0.90,
            "behavioral": 0.90,
        },
    }
    resp = client.post("/api/risk/calculate", json=payload)
    assert resp.status_code == 422
    assert "sum to approximately 1.0" in resp.json()["detail"]


def test_incident_carries_rich_risk_breakdown(client: TestClient) -> None:
    """Correlated incidents contain full transparent component breakdown and key factors."""
    ev = {
        "source_ip": "10.0.0.99",
        "user": "root_tester",
        "event_type": "resource_access",
        "action": "access_denied",
        "status": "denied",
        "resource": "/admin/vault/credentials",
    }
    resp = client.post("/api/events", json=ev)
    assert resp.status_code == 201

    incidents = client.get("/api/incidents").json()
    assert incidents["total"] == 1
    inc_id = incidents["items"][0]["incident_id"]

    detail = client.get(f"/api/incidents/{inc_id}").json()
    bdown = detail["risk_breakdown"]

    assert "composite_score" in bdown
    assert "weights" in bdown
    assert "components" in bdown
    assert "contributions" in bdown
    assert "key_factors" in bdown
    assert len(bdown["key_factors"]) > 0
    # Verify sensitive asset factor was recognized
    assert any("sensitive assets targeted" in f.lower() for f in bdown["key_factors"])
