# Phase 4 — Log ingestion, parsing, normalization & persistence

Ingestion pipeline on Laptop 2. Validates incoming events, normalizes diverse formats (JSON, CEF, Syslog, Key-Value) to the canonical schema, assigns sequential event IDs, and persists directly to SQLite.

## What was created / updated

| Path | Role |
|------|------|
| `backend/app/services/parser.py` | `LogParser` engine: alias resolution, timestamp parsing, sensitive value redaction, and multi-format log decoding (CEF, Syslog RFC 3164/5424, Key-Value/logfmt, Web CLF, JSON) |
| `backend/app/services/ingestion.py` | `IngestionService`: atomic batch handling, automatic sequential ID generator (`EVT-0001`...), duplicate/conflict checking (409), schema validation, and SQLite persistence |
| `backend/app/services/__init__.py` | Exported `IngestionService` and `LogParser` |
| `backend/app/models/schemas.py` | Enhanced `EventCreate` (allowing extra metadata attributes), added `EventBatchCreate` and `EventBatchResponse` |
| `backend/app/api/events.py` | Connected `POST /api/events` (single, batch `{ "events": [...] }`, JSON array, or plain text) and added `POST /api/events/parse` preview endpoint |
| `backend/app/api/health.py` | Updated `log_collector` component health to `ONLINE` and phase to `4` |
| `backend/app/database/seed.py` | Updated default seed component status for `log_collector` to `ONLINE` |
| `backend/app/config.py` | Set `implementation_phase` default to `4` |
| `backend/app/main.py` | Updated FastAPI app version to `0.4.0` |
| `backend/tests/test_ingestion.py` | Full test suite: single event, batch objects, array payloads, custom IDs, 409 conflict detection, 422 validation, secret redaction, alias mappings, timestamp parsing, raw log parsing, text/plain streaming, preview parse, and query filtering |
| `backend/tests/test_health.py` | Updated assertions for Phase 4 and `log_collector: ONLINE` |

## Normalized Event Contract

Incoming events are normalized to the canonical schema:

```json
{
  "event_id": "EVT-0001",
  "timestamp": "2026-10-08T17:00:00Z",
  "source_ip": "10.0.0.41",
  "destination_ip": "10.0.0.10",
  "user": "jdoe",
  "event_type": "authentication",
  "action": "login_failed",
  "status": "failure",
  "resource": "vpn-gateway",
  "protocol": "https",
  "source_device": "laptop-sim-01",
  "metadata": {},
  "raw": null,
  "ingested_at": "2026-10-08T17:00:01Z"
}
```

### Supported Input Formats

1. **Single JSON Event**:
   ```json
   {
     "user": "jdoe",
     "event_type": "authentication",
     "action": "login_failed",
     "source_ip": "10.0.0.41"
   }
   ```
   Returns `201 Created` with normalized `EventRead`.

2. **Batch Container Object**:
   ```json
   {
     "events": [
       { "user": "alice", "event_type": "authentication", "action": "login_failed" },
       { "user": "alice", "event_type": "authentication", "action": "login_success" }
     ]
   }
   ```
   Returns `201 Created` with `EventBatchResponse` (`{ "events": [...], "count": 2 }`).

3. **JSON Array of Events**:
   ```json
   [
     { "user": "bob", "event_type": "resource_access", "action": "access_denied" }
   ]
   ```
   Returns `201 Created` with `EventBatchResponse`.

4. **Common Event Format (CEF)**:
   ```text
   CEF:0|LogShield|SecurityLab|1.0|100|login_failed|5|src=10.0.0.41 dst=10.0.0.10 suser=jdoe act=login_failed proto=https
   ```

5. **Syslog Lines (RFC 3164 / 5424)**:
   ```text
   Oct 8 17:00:00 laptop-sim-01 sshd[1234]: Failed password for invalid user hacker from 203.0.113.195 port 44212 ssh2
   ```

6. **Key-Value / Logfmt**:
   ```text
   timestamp="2026-10-08T17:00:00Z" event_type=authentication action=login_failed user=jdoe src_ip=10.0.0.41
   ```

### Field Aliases & Normalization

- `src_ip`, `src`, `source`, `client_ip` → `source_ip`
- `dst_ip`, `dst`, `dest`, `target_ip` → `destination_ip`
- `username`, `suser`, `duser`, `usr`, `account` → `user`
- `cat`, `category`, `type` → `event_type`
- `act`, `operation`, `event` → `action`
- `res`, `target`, `uri`, `path` → `resource`
- `proto` → `protocol` (lowercased)
- `device`, `hostname`, `host` → `source_device`
- `result`, `outcome` → `status` (lowercased)
- Any non-canonical fields (e.g. `scenario`, `attempt`, `geo`) are automatically preserved in `metadata`.
- Any keys in metadata containing credentials or tokens (`password`, `secret`, `token`, `api_key`) are automatically redacted to `[REDACTED]`.

## Test and Verification

Run the test suite:

```powershell
cd C:\Users\kisho\LogShield\backend
.\.venv\Scripts\Activate.ps1
pytest -v
```

Manual API tests:

```powershell
# 1. Ingest single event
curl -X POST http://127.0.0.1:8000/api/events `
  -H "Content-Type: application/json" `
  -d '{"user": "analyst_test", "event_type": "authentication", "action": "login_failed", "source_ip": "10.0.0.41"}'

# 2. Ingest batch
curl -X POST http://127.0.0.1:8000/api/events `
  -H "Content-Type: application/json" `
  -d '{"events": [{"user": "user1", "event_type": "auth", "action": "login"}, {"user": "user2", "event_type": "auth", "action": "logout"}]}'

# 3. Ingest raw syslog via text/plain
curl -X POST http://127.0.0.1:8000/api/events `
  -H "Content-Type: text/plain" `
  -d 'Oct 8 17:00:00 laptop-sim-01 sshd[1234]: Failed password for invalid user jdoe from 10.0.0.41 port 22 ssh2'

# 4. Preview parser without saving to SQLite
curl -X POST http://127.0.0.1:8000/api/events/parse `
  -H "Content-Type: application/json" `
  -d '{"src": "192.168.1.100", "act": "login_failed", "cat": "authentication", "api_key": "secret_abc"}'

# 5. Check real-time SQLite statistics
curl http://127.0.0.1:8000/api/statistics
```

## Next

Phase 5 — Rule engine: stateful / threshold detection rules for brute force auth, privilege escalation, and suspicious lateral movement producing detection `alerts`.
