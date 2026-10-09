# Phase 5 — Rule engine & detection alerts

Stateful and threshold-based security detection rules on Laptop 2. Ingested events are automatically evaluated against active security rules to detect brute force auth, spraying, privilege elevation, unauthorized resource access, and abnormal network behavior, producing persistent detection `alerts`.

## What was created / updated

| Path | Role |
|------|------|
| `backend/app/detection/rules.py` | Suite of 6 security rules inheriting from `BaseRule`: sliding time windows, threshold evaluations, severity scoring, and transparent explanation messages |
| `backend/app/detection/engine.py` | `RuleEngine`: event/batch evaluation, sequential alert ID generation (`ALT-0001`...), SQLite alert persistence |
| `backend/app/detection/__init__.py` | Exported `RuleEngine`, `default_rule_engine`, `BaseRule`, `get_default_rules` |
| `backend/app/services/ingestion.py` | Connected `default_rule_engine` into `ingest_single` and `ingest_batch` pipelines |
| `backend/app/api/alerts.py` | Added `GET /api/alerts/rules` and `GET /api/alerts/{alert_id}` (with 404 handling) |
| `backend/app/api/health.py` | Updated `ai_engine` status to `ONLINE` |
| `backend/app/database/seed.py` | Updated default seed for `ai_engine` to `ONLINE` |
| `backend/app/config.py` | Updated `implementation_phase` default to `5` |
| `backend/app/main.py` | Updated FastAPI app version to `0.5.0` |
| `backend/tests/test_rules.py` | Complete test suite for all rules, thresholds, alert persistence, ID formatting, statistics incrementing, and API endpoints |
| `backend/tests/test_health.py` | Updated assertions for Phase 5 and `ai_engine: ONLINE` |

## Detection Rules Suite

| Rule ID | Name | Trigger Condition | Severity | Window |
|---------|------|-------------------|----------|--------|
| `RULE-AUTH-001` | Repeated Authentication Failures | $\ge 3$ failed logins for the same user or source IP | `MEDIUM` ($\ge 3$), `HIGH` ($\ge 5$) | 300s |
| `RULE-AUTH-002` | Successful Login Following Failures | Successful login after $\ge 2$ recent login failures for the same user | `HIGH` | 300s |
| `RULE-AUTH-003` | Password Spraying Activity | Single source IP targeting $\ge 3$ distinct user accounts | `HIGH` | 300s |
| `RULE-ACC-001` | Unauthorized Resource Access | Access denied / unauthorized request to restricted resources (`/etc/shadow`, `secrets`, etc.) | `MEDIUM` / `HIGH` | 60s |
| `RULE-PRV-001` | Privileged Command Execution | Execution of `sudo`, root elevation, or administrative maintenance actions | `HIGH` | 60s |
| `RULE-NET-001` | Abnormal Network Activity | Network port scan, outbound scan, or packet drops | `MEDIUM` / `HIGH` | 300s |

## Alert Schema

Generated alerts are stored in the `alerts` SQLite table and served by `GET /api/alerts`:

```json
{
  "alert_id": "ALT-0001",
  "created_at": "2026-10-09T00:10:00Z",
  "source": "rule",
  "severity": "HIGH",
  "title": "Successful Login After Multiple Failures",
  "message": "User 'jdoe' logged in successfully after 3 recent failed authentication attempts within 300s.",
  "event_id": "EVT-0004",
  "incident_id": null,
  "extras": {
    "rule_id": "RULE-AUTH-002",
    "prior_failures": 3,
    "user": "jdoe",
    "source_ip": "10.0.0.41",
    "window_seconds": 300
  }
}
```

## Test and Verification

Run the full pytest suite:

```powershell
cd C:\Users\kisho\LogShield\backend
.\.venv\Scripts\Activate.ps1
pytest -v
```

Manual verification:

```powershell
# 1. Inspect registered detection rules
curl http://127.0.0.1:8000/api/alerts/rules

# 2. Simulate brute-force logins (triggers RULE-AUTH-001 on attempt 3)
curl -X POST http://127.0.0.1:8000/api/events -H "Content-Type: application/json" -d '{"user": "alice", "event_type": "authentication", "action": "login_failed", "source_ip": "10.0.0.50"}'
curl -X POST http://127.0.0.1:8000/api/events -H "Content-Type: application/json" -d '{"user": "alice", "event_type": "authentication", "action": "login_failed", "source_ip": "10.0.0.50"}'
curl -X POST http://127.0.0.1:8000/api/events -H "Content-Type: application/json" -d '{"user": "alice", "event_type": "authentication", "action": "login_failed", "source_ip": "10.0.0.50"}'

# 3. View generated detection alerts
curl http://127.0.0.1:8000/api/alerts

# 4. View updated dashboard statistics (threats_detected = 1)
curl http://127.0.0.1:8000/api/statistics
```

## Next

Phase 6 — Isolation Forest anomaly detection (unsupervised machine learning on sliding window feature vectors).
