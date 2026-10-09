# Phase 1 — what was created

Architecture and folder skeleton only. No running API, no ML, no UI.

## Files

| Path | Purpose |
|------|---------|
| `README.md` | Project overview and phase tracker |
| `.env.example` | Configurable hosts, ports, weights, correlation window |
| `.gitignore` | Python/Node/local DB ignores |
| `docs/architecture.md` | Three-laptop design, pipeline, schema, risk |
| `docs/api.md` | REST + WebSocket contract |
| `docs/demo.md` | Live demo narrative |
| `backend/` | Engine package layout + placeholder modules |
| `frontend/` | SOC UI layout placeholders |
| `simulator/` | Scenario package placeholders |

## How to verify Phase 1

```powershell
# Windows PowerShell — from the repo root
Get-ChildItem -Recurse -Name | Sort-Object
```

```bash
# Linux / macOS
find . -type f -o -type d | sort
```

You should see `backend/app/{api,models,services,detection,correlation,risk,database,websocket}`, `frontend/src/{components,pages,services,hooks,types}`, `simulator/scenarios`, and `docs/`.

There is nothing to start with `uvicorn` or `npm` yet. That is Phase 2 / 11.

## Next phase

**Phase 2 — FastAPI backend skeleton:** `main.py`, health/system-status stubs, CORS from env, run instructions.
