# Phase 2 — FastAPI backend skeleton

Runnable HTTP engine on Laptop 2. No SQLite, ingestion, detection, or WebSocket yet.

## What was created

| Path | Role |
|------|------|
| `backend/app/config.py` | `LOGSHIELD_*` settings, CORS list, public URL |
| `backend/app/main.py` | FastAPI app + CORS |
| `backend/app/api/health.py` | `/api/health`, `/api/system-status` |
| `backend/app/api/events.py` | Stub list/get; POST returns 501 |
| `backend/app/api/incidents.py` | Stub list/get; PATCH returns 501 |
| `backend/app/api/alerts.py` | Empty list |
| `backend/app/api/statistics.py` | Computed zeros (not fake threats) |
| `backend/app/models/schemas.py` | Response models |
| `backend/tests/test_health.py` | Smoke tests |
| `backend/requirements.txt` | Pinned FastAPI stack |

System status is honest: `system=ONLINE`, `ai_engine=NOT_READY`, `log_collector=NOT_READY`.

## Run (Laptop 2)

Windows PowerShell:

```powershell
cd C:\Users\kisho\LogShield\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example ..\.env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Bind host/port also come from env; `--host 0.0.0.0` is required so other laptops can connect. Set `LOGSHIELD_SERVER_HOST` in `.env` to this laptop’s LAN IP (example `192.168.1.20`).

## Test

```powershell
cd C:\Users\kisho\LogShield\backend
.\.venv\Scripts\Activate.ps1
pytest -q
```

With the server running:

```powershell
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/system-status
```

Open `http://127.0.0.1:8000/docs` for Swagger.

## Next

Phase 3 — SQLite schema and connection for events, incidents, alerts, users, system_status.
