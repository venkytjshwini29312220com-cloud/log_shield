# LogShield SOC dashboard (Laptop 3)

React SOC UI. All numbers come from Laptop 2 (`LOGSHIELD_SERVER_HOST`).

**Phase 1:** folder layout only. App scaffolding is Phase 11; investigation page is Phase 12.

## Planned pages

1. Overview
2. Live Events
3. Active Incidents
4. Incident Investigation (centerpiece)
5. Threat Analytics
6. Log Explorer
7. System Status

## Intended run (after Phase 11)

```powershell
cd frontend
npm install
copy ..\.env.example .env
# set VITE_LOGSHIELD_API later
npm run dev -- --host
```
