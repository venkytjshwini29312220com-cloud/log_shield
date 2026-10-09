# Phase 7 — Event Correlation Engine & Incident Management

Event correlation and incident reconstruction layer on Laptop 2. Correlates individual events and detection alerts (both rule-based and ML anomaly alerts) across a sliding time window (default 300s) into unified, cohesive security incidents with automated timeline reconstruction, multi-stage kill chain tracking, explainable risk scores, and actionable analyst recommendations.

## What was created / updated

| Path | Role |
|------|------|
| `backend/app/correlation/engine.py` | Core `CorrelationEngine`: join-key matching (`user`, `source_ip`, `resource`, indirect event links), sliding correlation window (300s), sequential collision-free incident ID allocation (`INC-1001`...), kill-chain stage evaluation, dynamic risk scoring, and auto timeline sequence generation |
| `backend/app/correlation/__init__.py` | Exported `CorrelationEngine` and `default_correlation_engine` singleton |
| `backend/app/services/ingestion.py` | Integrated `default_correlation_engine.correlate_event` into single and batch ingestion pipelines; added `POST /api/events/batch` route |
| `backend/app/models/schemas.py` | Added `IncidentDetail` schema with full chronologically linked `events: list[EventRead]` and `alerts: list[AlertRead]` |
| `backend/app/api/incidents.py` | Updated `GET /api/incidents/{incident_id}` to return `IncidentDetail` with sequenced event timelines and correlated alerts |
| `backend/app/api/statistics.py` | Computed real-time incident metrics from SQLite: `active_incidents`, `critical_incidents`, and `current_risk` |
| `backend/app/config.py` | Updated `implementation_phase` default to `7` |
| `backend/app/main.py` | Bumped app version to `0.7.0` and updated OpenAPI documentation |
| `backend/tests/test_correlation.py` | Full test suite: Scenario F multi-stage correlation, join-key matching, correlation window expiration, incident status/severity filtering, and 404 handling |
| `backend/tests/test_health.py` | Updated Phase 7 assertions |

## Correlation Architecture & Join Keys

The `CorrelationEngine` groups events into an existing open incident if:
1. The incident's status is open (`NEW`, `INVESTIGATING`, or `CONTAINED`).
2. The incident's `last_seen` timestamp falls within the correlation window (`LOGSHIELD_CORRELATION_WINDOW_SECONDS`, default 300 seconds).
3. The incoming event shares any primary or indirect join keys:
   - **User identity:** `event.user == incident.affected_user` or matches an event already attached to the incident.
   - **Source IP:** `event.source_ip == incident.source_ip` or matches any previously attached event's source/destination IP (identifying pivot activity).
   - **Resource:** `event.resource == incident.resource` (identifying multi-source targeting of a sensitive asset).

If no active incident matches and the incoming event is suspicious or triggers an alert, a new incident is created (`INC-1001`, `INC-1002`...).

## Scenario F: Multi-Stage Attack Correlation (Centerpiece)

The centerpiece demonstration validates that a multi-stage intrusion sequence correlates into **exactly one incident** rather than fragmenting into multiple disparate tickets:

```
[Failed Logins (3x)] ---> [Successful Login] ---> [Access Denied on Vault] ---> [Port Scan]
       |                          |                        |                         |
  RULE-AUTH-001             RULE-AUTH-002            RULE-ACC-001              RULE-NET-001
       \                          |                        /                         /
        \                         |                       /                         /
         +-------------------------------------------------------------------------+
                                          |
                              Single Unified Incident
                              ID: INC-1001
                              Severity: CRITICAL
                              Risk Score: 94 / 100
                              Stages: 3 / 3 (Kill-Chain Complete)
```

### Kill-Chain Stages Tracked

1. **Authentication / Initial Access:** Failed brute-force attempts followed by legitimate credential use.
2. **Privilege Escalation / Resource Access:** Unauthorized attempts against sensitive resources (`/finance/records`, `/admin/payroll`, sudo).
3. **Reconnaissance / Lateral Movement / Exfiltration:** Network scanning, port sweeps, or abnormal outbound connections.

When all 3 stages occur in sequence, the incident elevates to `CRITICAL` severity with an explainable risk score of `94`, generating actionable response recommendations (isolate source host, revoke compromised credentials, terminate active sessions).

## Test and Verification

Run the complete test suite (all 43 tests passing):

```powershell
cd C:\Users\kisho\LogShield\backend
.\.venv\Scripts\Activate.ps1
pytest -v
```

### Verification via REST API

```powershell
# 1. Ingest Scenario F multi-stage sequence in one batch:
curl -X POST http://127.0.0.1:8000/api/events/batch `
  -H "Content-Type: application/json" `
  -d '{"events": [
    {"source_ip": "10.0.0.99", "user": "mholmes", "event_type": "authentication", "action": "login_failed", "status": "failure"},
    {"source_ip": "10.0.0.99", "user": "mholmes", "event_type": "authentication", "action": "login_failed", "status": "failure"},
    {"source_ip": "10.0.0.99", "user": "mholmes", "event_type": "authentication", "action": "login_failed", "status": "failure"},
    {"source_ip": "10.0.0.99", "user": "mholmes", "event_type": "authentication", "action": "login_success", "status": "success"},
    {"source_ip": "10.0.0.99", "user": "mholmes", "event_type": "resource_access", "action": "access_denied", "resource": "/finance/records", "status": "denied"},
    {"source_ip": "10.0.0.99", "user": "mholmes", "event_type": "network", "action": "port_scan", "destination_ip": "10.0.0.250", "status": "success"}
  ]}'

# 2. Verify only 1 incident exists:
curl http://127.0.0.1:8000/api/incidents

# 3. Inspect detailed incident with reconstructed chronological timeline:
curl http://127.0.0.1:8000/api/incidents/INC-1001

# 4. Check real-time dashboard statistics:
curl http://127.0.0.1:8000/api/statistics
```
