# Phase 10 — Real-time WebSocket Fan-Out (`/ws/events`)

Real-time telemetry distribution layer on Laptop 2. Connects SOC analysts and downstream dashboards (Laptop 3) to asynchronous security events, alerts, incident correlation updates, and explainable risk modifications without polling.

## Fan-Out Telemetry Contract

WebSocket URL: `ws://$LOGSHIELD_SERVER_HOST:$LOGSHIELD_SERVER_PORT/ws/events`

Every message follows a uniform JSON envelope:

```json
{
  "type": "<event_type>",
  "timestamp": "2026-10-09T04:15:00.123456+00:00",
  "payload": { ... }
}
```

| `type` | Trigger Condition | Payload Summary |
|--------|-------------------|-----------------|
| `system.status` | Initial client connection handshake, or heartbeat | Subsystem operational states (`ONLINE`), active connections count, current phase |
| `event.created` | Successful log ingestion via single, batch, or text | Normalized event record (`event_id`, `timestamp`, `source_ip`, `user`, `action`, `status`, etc.) |
| `alert.created` | Deterministic rule match or Isolation Forest anomaly alert | Detection notice (`alert_id`, `source`, `severity`, `title`, `message`, `event_id`, `incident_id`) |
| `incident.created` | Correlation engine opens a new security incident | Correlated incident details (`incident_id`, `severity`, `risk_score`, `status`, `summary`, `affected_user`, etc.) |
| `incident.updated` | Incident state progressed, new event linked, or analyst triaged (`PATCH` / notes) | Updated incident status, risk breakdown, latest timeline bounds |
| `risk.changed` | Incident composite risk score or severity band recomputed | `incident_id`, `risk_score`, `previous_risk_score`, `severity`, and component contributions |
| `pong` | Server response to client keepalive ping | Ping-pong keepalive acknowledgement (`{"status": "ok"}`) |

## Connection Lifecycle & Resilience

```text
Laptop 3 (SOC Dashboard)                    Laptop 2 (LogShield Engine)
          |                                             |
          |-------- WS Connect /ws/events ------------->|
          |<------- system.status (welcome handshake) --| (Active connections: +1)
          |                                             |
          | [Event Ingestion / Detection / Correlation] |
          |<------- event.created ----------------------|
          |<------- alert.created ----------------------|
          |<------- incident.created -------------------|
          |<------- risk.changed -----------------------|
          |                                             |
          |-------- ping ------------------------------>|
          |<------- pong -------------------------------|
          |                                             |
          | [Analyst Triages Incident: PATCH / Note]    |
          |<------- incident.updated -------------------|
          |                                             |
          |-------- Disconnect / Close ---------------->| (Active connections: -1, cleaned cleanly)
```

- **Threadsafe & Async-Compatible:** `ConnectionManager` supports both asynchronous broadcasting (`broadcast`) and threadsafe synchronous execution (`broadcast_sync`) from background threadpools.
- **Fail-Safe Client Pruning:** When a client abruptly terminates or encounters transport errors, dead connections are pruned from the connection pool without affecting other connected subscribers.
- **Multi-Tenant Fan-Out:** Multiple dashboards, browser tabs, or automation agents can subscribe simultaneously to the same telemetry stream.

## Endpoints Implemented

| Method | Endpoint | Description |
|--------|----------|-------------|
| `WS` | `/ws/events` | Real-time WebSocket connection for streaming SOC telemetry |
| `GET` | `/api/websocket/status` | Inspect WebSocket subsystem status, active subscriber count, and supported message types |
| `POST` | `/api/websocket/broadcast` | Operational endpoint to broadcast manual telemetry or administrative notices |

## What was created / updated

| Path | Role |
|------|------|
| `backend/app/websocket/manager.py` | `ConnectionManager` with connection pooling, multi-client async broadcasting, synchronous scheduling, and typed telemetry builders |
| `backend/app/websocket/router.py` | `/ws/events` WebSocket endpoint with welcome handshake, ping-pong handler, and REST status inspection endpoints |
| `backend/app/websocket/__init__.py` | Exported `ws_manager`, `ConnectionManager`, and `websocket_router` |
| `backend/app/models/schemas.py` | Added `WebSocketEventType`, `WebSocketMessage`, `WebSocketStatusResponse`, and `WebSocketBroadcastRequest` |
| `backend/app/services/ingestion.py` | Broadcasts `event.created` upon persistence and `alert.created` for rule & ML detections |
| `backend/app/correlation/engine.py` | Broadcasts `incident.created`, `incident.updated`, and `risk.changed` during kill-chain correlation |
| `backend/app/api/incidents.py` | Broadcasts `incident.updated` during analyst status transitions and note attachments |
| `backend/app/api/events.py` | Added cooperative event loop yield to flush broadcast queues prior to returning HTTP responses |
| `backend/app/api/health.py` | Registered `websocket` component health in `/api/system-status` |
| `backend/app/config.py` | Bumped `implementation_phase = 10` |
| `backend/app/main.py` | Registered `websocket_router`, lifespan event loop registration, and bumped version to `0.10.0` |
| `backend/tests/test_websocket.py` | 8 comprehensive tests: connection handshake, ping-pong, REST status, event broadcast, alert/incident broadcast, analyst updates, multi-client delivery, and manual broadcast |
| `backend/tests/test_health.py` | Updated assertions for Phase 10 and WebSocket component status |

## Verification & Testing

```powershell
cd C:\Users\kisho\LogShield\backend
.\.venv\Scripts\Activate.ps1
pytest -v
```

All 66 tests passing.

### Demonstration

```powershell
# 1. Query WebSocket subsystem health and subscriber count:
curl http://127.0.0.1:8000/api/websocket/status

# 2. Connect via WebSocket client (e.g., websocat or python client):
# websocat ws://127.0.0.1:8000/ws/events
# Expected first packet:
# {"type":"system.status","timestamp":"...","payload":{"system":"ONLINE","websocket":"ONLINE","active_connections":1,"phase":10}}

# 3. In another terminal, ingest a log event:
curl -X POST http://127.0.0.1:8000/api/events `
  -H "Content-Type: application/json" `
  -d '{"timestamp": "2026-10-09T04:00:00Z", "source_ip": "10.0.0.41", "user": "jdoe", "event_type": "authentication", "action": "login_failed", "status": "failure", "resource": "vpn-gateway"}'

# WebSocket subscriber immediately receives event.created, alert.created, and incident.created frames.
```
