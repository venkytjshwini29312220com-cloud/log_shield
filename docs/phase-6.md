# Phase 6 — Isolation Forest anomaly detection

Unsupervised anomaly detection layer on Laptop 2. Extracts 10-dimensional behavioral features across sliding time windows in SQLite, scores behavioral risk (0–100), and emits ML-sourced alerts when anomalous bursts or deviations occur.

## What was created / updated

| Path | Role |
|------|------|
| `backend/app/detection/features.py` | Windowed behavioral feature extraction (10 features: event volume, failed auth count, fail ratio, unique IPs, unique users, unique event types, auth ratio, access ratio, network ratio, privileged command count) |
| `backend/app/detection/isolation_forest.py` | Pure-Python `IsolationForestDetector`: ensemble of 50 Isolation Trees, pre-trained on synthetic normal baseline traffic, calibrated 0–100 risk scoring (not attack probability), and automatic ML alert generation ($\ge 65$ threshold) |
| `backend/app/detection/__init__.py` | Exported `IsolationForestDetector`, `default_ml_detector`, `extract_features_from_db`, and `FEATURE_NAMES` |
| `backend/app/api/ml.py` | Added `GET /api/ml/status` (model metadata, feature list, threshold) and `POST /api/ml/score` (score arbitrary feature vectors or feature dictionaries) |
| `backend/app/services/ingestion.py` | Integrated `default_ml_detector.evaluate_event` into `ingest_single` and `ingest_batch` pipelines |
| `backend/app/main.py` | Registered `ml.router`, updated app version to `0.6.0`, and updated description |
| `backend/app/config.py` | Updated `implementation_phase` default to `6` |
| `backend/app/api/health.py` | Updated `ai_engine` component detail to reflect active hybrid detection (Rule Engine + Isolation Forest) |
| `backend/app/database/seed.py` | Updated default seed for `ai_engine` to Phase 6 status |
| `backend/requirements.txt` | Added `numpy` and `scikit-learn` dependencies |
| `backend/tests/test_ml.py` | Complete test suite: model status, vector scoring, dictionary scoring, feature extraction from events, and burst anomaly alert generation |
| `backend/tests/test_health.py` | Updated assertions for Phase 6 |
| `backend/tests/test_rules.py` | Updated source-filtered assertions for rule engine |

## Feature Vector (10 Dimensions)

| Feature | Description | Normal Baseline Range |
|---------|-------------|-----------------------|
| `event_count` | Total events in the sliding window | 1 – 30 |
| `failed_auth_count` | Number of failed authentication attempts | 0 – 2 |
| `fail_ratio` | Ratio of failed auths to total auth events | 0.0 – 0.2 |
| `unique_source_ips` | Count of distinct source IPs in window | 1 – 3 |
| `unique_users` | Count of distinct users in window | 1 – 3 |
| `unique_event_types` | Count of distinct event types in window | 1 – 3 |
| `auth_ratio` | Percentage of authentication events | 0.2 – 0.8 |
| `access_ratio` | Percentage of resource access events | 0.1 – 0.5 |
| `network_ratio` | Percentage of network events | 0.0 – 0.5 |
| `privileged_count` | Number of privileged / sudo executions | 0.0 |

## Risk Scoring

- **Scale:** Strictly 0–100 integer score (per architecture guidelines: *never attack probabilities*).
- **Normal baseline traffic:** Scores 0–35 (LOW).
- **Unusual / elevated activity:** Scores 36–64 (MEDIUM).
- **Anomalous bursts & deviations:** Scores 65–84 (HIGH, triggers `Alert` with `source="ml"`).
- **Critical multi-vector anomaly:** Scores 85–100 (CRITICAL).

## Test and Verification

Run the full pytest suite:

```powershell
cd C:\Users\kisho\LogShield\backend
.\.venv\Scripts\Activate.ps1
pytest -v
```

Manual verification:

```powershell
# 1. Inspect ML model status
curl http://127.0.0.1:8000/api/ml/status

# 2. Score a normal feature vector
curl -X POST http://127.0.0.1:8000/api/ml/score `
  -H "Content-Type: application/json" `
  -d '{"features": [10.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.5, 0.5, 0.0, 0.0]}'

# 3. Score an anomalous feature vector (spikes, 90% failures, sudo actions)
curl -X POST http://127.0.0.1:8000/api/ml/score `
  -H "Content-Type: application/json" `
  -d '{"features": [100.0, 90.0, 0.9, 10.0, 8.0, 4.0, 0.9, 0.05, 0.05, 5.0]}'

# 4. Ingest an anomalous burst of events
curl -X POST http://127.0.0.1:8000/api/events `
  -H "Content-Type: application/json" `
  -d '{"events": [{"user": "u1", "event_type": "auth", "action": "login_failed", "source_ip": "1.1.1.1"}, {"user": "u2", "event_type": "auth", "action": "login_failed", "source_ip": "1.1.1.2"}, {"user": "u3", "event_type": "privileged_command", "action": "sudo_bash"}]}'

# 5. Query ML-specific alerts
curl http://127.0.0.1:8000/api/alerts?source=ml
```

## Next

Phase 7 — Correlation engine (group related events and alerts within `LOGSHIELD_CORRELATION_WINDOW_SECONDS` by user, IP, resource, and multi-stage kill chain into preliminary incidents).
