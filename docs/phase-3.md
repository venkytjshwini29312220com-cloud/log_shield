# Phase 3 — SQLite database

Persistent store on Laptop 2. Ingestion still returns 501 until Phase 4.

## Tables

| Table | Purpose |
|-------|---------|
| `events` | Normalized log events |
| `incidents` | Correlated incidents + explanation/risk |
| `incident_events` | Many-to-many timeline membership |
| `alerts` | Rule/ML/correlation notices |
| `users` | Analyst identities (seeded `analyst`) |
| `system_status` | Component health rows |

## What was created

| Path | Role |
|------|------|
| `backend/app/models/orm.py` | SQLAlchemy ORM models (`Event`, `Incident`, `Alert`, `User`, `SystemStatus`) |
| `backend/app/models/schemas.py` | Pydantic response and domain schemas (`EventRead`, `EventCreate`, `AlertRead`, `IncidentRead`, `UserRead`, pagination models) |
| `backend/app/database/session.py` | Engine, foreign keys PRAGMA, sessions, `init_db` |
| `backend/app/database/seed.py` | Default analyst (`analyst`) + status rows + standalone CLI execution |
| `backend/app/main.py` | Lifespan calls `init_db()` on engine startup |
| `backend/app/api/statistics.py` | Real-time `COUNT`/`MAX` aggregates queried from SQLite |
| `backend/app/api/events.py` | `GET /api/events` (filtering, pagination) and `GET /api/events/{id}` (404 handling) connected to SQLite; `POST /api/events` returns 501 (Phase 4) |
| `backend/app/api/alerts.py` | `GET /api/alerts` with severity/source filtering and pagination from SQLite |
| `backend/app/api/incidents.py` | `GET /api/incidents` and `GET /api/incidents/{id}` connected to SQLite; `PATCH` returns 501 (Phase 9) |
| `backend/tests/test_database.py` | Schema verification, seeded analyst check, event round-trip, query filtering, and 404 tests |

Database URL: `LOGSHIELD_DATABASE_URL` (default `sqlite:///./data/logshield.db`, resolved under `backend/`).

## Run

```powershell
cd C:\Users\kisho\LogShield\backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On startup the engine creates `backend/data/logshield.db` if missing. Alternatively, seed explicitly:

```powershell
python -m app.database.seed
```

## Test

```powershell
cd C:\Users\kisho\LogShield\backend
.\.venv\Scripts\python.exe -m pytest -v
```

Manual verification:

```powershell
curl http://127.0.0.1:8000/api/system-status
curl http://127.0.0.1:8000/api/statistics
curl http://127.0.0.1:8000/api/events
curl http://127.0.0.1:8000/api/alerts
curl http://127.0.0.1:8000/api/incidents
```

`components.database.status` is `ONLINE`. Statistics and list endpoints return clean, empty arrays from SQLite until events are ingested in Phase 4.

## Next

Phase 4 — `POST /api/events`: log ingestion, parsing, normalization to standard event schema, and database persistence.
