# API contract (Phase 1)

Base URL: `http://$LOGSHIELD_SERVER_HOST:$LOGSHIELD_SERVER_PORT`

Implemented in Phase 2+. This document is the target contract.

## Health

### `GET /api/health`

```json
{ "status": "ok", "service": "logshield-engine" }
```

### `GET /api/system-status`

```json
{
  "system": "ONLINE",
  "ai_engine": "ONLINE",
  "log_collector": "ONLINE",
  "ml_model": "prototype Isolation Forest anomaly detector",
  "correlation_window_seconds": 300
}
```

## Events

### `POST /api/events`

Ingest one event or a batch `{ "events": [ ... ] }`. Validates against the normalized schema. Returns stored event(s) with assigned `event_id`.

### `GET /api/events`

Query: `limit`, `offset`, `user`, `source_ip`, `event_type`, `since`, `until`.

### `GET /api/events/{event_id}`

404 if missing.

## Incidents

### `GET /api/incidents`

Query: `status`, `severity`, `limit`.

### `GET /api/incidents/{incident_id}`

Includes timeline, evidence, risk breakdown, related events, explanation, recommendation.

### `PATCH /api/incidents/{incident_id}`

Body: `{ "status": "INVESTIGATING" }` (allowed statuses only).

## Alerts and stats

### `GET /api/alerts`

Detection notices that may later merge into incidents.

### `GET /api/statistics`

Dashboard cards: total events, threats detected, active incidents, critical incidents, current risk. **Computed from SQLite, never hardcoded.**

## WebSocket

### `WS /ws/events`

JSON messages:

| `type` | When |
|--------|------|
| `event.created` | New ingested event |
| `alert.created` | Rule or ML alert |
| `incident.created` | Correlation opened an incident |
| `incident.updated` | Risk, severity, or status changed |
| `risk.changed` | Score update on an incident |
| `system.status` | Heartbeat / component health |

Example:

```json
{
  "type": "incident.created",
  "payload": {
    "incident_id": "INC-1042",
    "severity": "CRITICAL",
    "risk_score": 94,
    "status": "NEW"
  }
}
```

## Errors

JSON `{ "detail": "..." }` with 4xx/5xx. Validation errors use FastAPI’s standard 422 body.
