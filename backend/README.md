# LogShield backend (Laptop 2)

FastAPI engine: ingest → parse → detect → correlate → risk → incidents → WebSocket.

**Phase 3:** SQLite schema and startup initialization. `POST /api/events` is still 501.

## Run

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example ..\.env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The database file is created at `backend/data/logshield.db` (override with `LOGSHIELD_DATABASE_URL`).

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Live checks

- http://127.0.0.1:8000/api/health
- http://127.0.0.1:8000/api/system-status (`components.database` should be ONLINE)
- http://127.0.0.1:8000/api/statistics (zeros until ingestion)
- http://127.0.0.1:8000/docs
