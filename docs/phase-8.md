# Phase 8 — Weighted Risk Scoring Engine & Severity Classification

Computes transparent, configurable, explainable risk scores (0–100) and severity classifications across correlated incidents. Displaces black-box probability guesses with a defensible, multi-component security model adhering to the core principle: **Risk Score: N/100, never attack probabilities**.

## Formula & Component Weights

```text
risk = round(100 * (
  w_rule * rule_score
  + w_ml * ml_score
  + w_corr * correlation_score
  + w_beh * behavioral_score
))
```

| Component | Default Weight | Range | Role & Evaluation Criteria |
|-----------|----------------|-------|----------------------------|
| `rule_score` | 30% (`0.30`) | 0–100 | Severity and count of triggered deterministic detection rules (multi-rule amplification) |
| `ml_score` | 30% (`0.30`) | 0–100 | Isolation Forest unsupervised anomaly risk or activity density deviations |
| `correlation_score` | 25% (`0.25`) | 0–100 | Progression across kill-chain stages (Authentication &rarr; Privilege Access &rarr; Network Exfiltration) |
| `behavioral_score` | 15% (`0.15`) | 0–100 | High-value asset targeting (`finance`, `admin`, `vault`, `payroll`, `root`), brute-force success patterns, and rapid burst timing |

## Severity Bands

| Band | Score Range | Operational Meaning |
|------|-------------|---------------------|
| `LOW` | 0 – 30 | Routine or low-confidence anomaly; logged for situational awareness |
| `MEDIUM` | 31 – 60 | Isolated security event or elevated baseline traffic; automated monitoring |
| `HIGH` | 61 – 80 | Multi-domain activity or high-severity rule violation; analyst review recommended |
| `CRITICAL` | 81 – 100 | Multi-stage kill-chain intrusion or high-confidence compromise; urgent containment required |

## What was created / updated

| Path | Role |
|------|------|
| `backend/app/risk/engine.py` | `RiskEngine` computing composite score, severity bands, and rich transparent `risk_breakdown` with contribution points |
| `backend/app/risk/__init__.py` | Exported `RiskEngine`, `default_risk_engine`, and `score_to_severity` |
| `backend/app/api/risk.py` | REST endpoints: `GET /api/risk/weights` and `POST /api/risk/calculate` for simulation |
| `backend/app/models/schemas.py` | Added `RiskWeightsResponse`, `RiskCalculateRequest`, and `RiskCalculateResponse` |
| `backend/app/correlation/engine.py` | Integrated `default_risk_engine.calculate_incident_risk` to power incident risk evaluations |
| `backend/app/config.py` | Configurable weights (`LOGSHIELD_WEIGHT_RULE`, etc.) and `implementation_phase = 8` |
| `backend/app/main.py` | Registered `risk.router` and bumped version to `0.8.0` |
| `backend/tests/test_risk.py` | Test suite covering formula calculations, bounds, weights API, calculation simulation, and breakdown verification |
| `backend/tests/test_health.py` | Updated assertions for Phase 8 |

## Scenario F Risk Breakdown (Centerpiece Calibration)

For the Scenario F multi-stage intrusion sequence:
- `rule_score` = 95 &rarr; Contribution: **28.5 pts**
- `ml_score` = 90 &rarr; Contribution: **27.0 pts**
- `correlation_score` = 100 &rarr; Contribution: **25.0 pts**
- `behavioral_score` = 90 &rarr; Contribution: **13.5 pts**
- **Composite Score:** $28.5 + 27.0 + 25.0 + 13.5 = 94$ (**CRITICAL**)

Each correlated incident stores the exact mathematical contribution breakdown in `incident.risk_breakdown` for the analyst investigation view.

## Verification & Testing

```powershell
cd C:\Users\kisho\LogShield\backend
.\.venv\Scripts\Activate.ps1
pytest -v
```

All 51 tests passing.

### API Demonstration

```powershell
# 1. Inspect current weights and severity bands:
curl http://127.0.0.1:8000/api/risk/weights

# 2. Simulate composite risk calculation:
curl -X POST http://127.0.0.1:8000/api/risk/calculate `
  -H "Content-Type: application/json" `
  -d '{"rule_score": 95, "ml_score": 90, "correlation_score": 100, "behavioral_score": 90}'
```
