# Phase 13 — Three-Laptop Network Configuration & Simulator

Hardens the deployment for a real three-laptop LAN hackathon demo. No traffic is routed over the public internet; everything stays on the local network switch.

## Network Topology

```
┌─────────────────┐     HTTP POST /api/events      ┌──────────────────────────────────┐
│  Laptop 1       │ ──────────────────────────────► │  Laptop 2  (AI Engine)           │
│  Simulator      │                                  │  FastAPI 0.0.0.0:8000            │
│  python -m sim  │                                  │  SQLite   ./data/logshield.db    │
└─────────────────┘                                  │  WS       /ws/events             │
                                                     └──────────┬───────────────────────┘
                                                                │  WS + REST
                                                                ▼
                                                     ┌──────────────────────────────────┐
                                                     │  Laptop 3  (SOC Dashboard)       │
                                                     │  React Vite  :5173               │
                                                     │  VITE_LOGSHIELD_API=http://...   │
                                                     └──────────────────────────────────┘
```

## Configuration by Machine

### Laptop 2 — AI Engine Server

```bash
# .env  (copy from .env.example, edit one line)
LOGSHIELD_BIND_HOST=0.0.0.0          # listen on all interfaces
LOGSHIELD_BIND_PORT=8000
LOGSHIELD_SERVER_HOST=192.168.1.20   # Laptop 2 LAN IP
LOGSHIELD_CORS_ORIGINS=http://192.168.1.30:5173,http://192.168.1.30:4173,http://localhost:5173
```

```powershell
# Start engine
cd LogShield\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Laptop 1 — Simulator

```bash
# .env
LOGSHIELD_SERVER_HOST=192.168.1.20   # Laptop 2 LAN IP
LOGSHIELD_SERVER_PORT=8000
```

```powershell
pip install requests python-dotenv
python -m simulator                  # interactive menu
python -m simulator -s F             # demo kill-chain immediately
```

### Laptop 3 — SOC Dashboard

```bash
# frontend/.env
VITE_LOGSHIELD_API=http://192.168.1.20:8000
```

```powershell
cd LogShield\frontend
npm install
npm run dev                          # http://localhost:5173
# or serve the pre-built dist:
npm run build
npx serve dist -l 5173
```

## Firewall / Network Checklist

| Port | Protocol | Required on Laptop 2 |
|------|----------|----------------------|
| 8000 | TCP | Inbound from Laptop 1 (POST /api/events) |
| 8000 | TCP | Inbound from Laptop 3 (REST + WS) |

Windows Firewall quick-allow:
```powershell
# Run as Administrator on Laptop 2
netsh advfirewall firewall add rule name="LogShield 8000" `
    dir=in action=allow protocol=TCP localport=8000
```

## Simulator CLI Reference

```powershell
# All scenarios with 0.4s delay (default)
python -m simulator -s ALL

# Fastest possible (for bandwidth tests)
python -m simulator -s F --delay 0.05 --loop

# Quiet mode (no per-event output)
python -m simulator -s F -q
```

## Simulator Scenarios

| ID | Scenario | Events | Expected Outcome |
|----|----------|--------|-----------------|
| A | Normal baseline | 8 | No alerts (benign) |
| B | Brute force | 12 | `MEDIUM`/`HIGH` alert — rule engine |
| C | Credential stuffing | 10 | Anomaly alert — Isolation Forest ML |
| D | Privilege escalation | 4 | Multi-rule alert chain |
| E | Lateral movement | 4 | `HIGH` incident — correlation |
| F | Full kill-chain ⭐ | 8 | `CRITICAL` correlated incident — all engines |

## What was created / updated

| Path | Role |
|------|------|
| `simulator/event_generator.py` | 6 deterministic attack scenario factories (A–F) |
| `simulator/client.py` | HTTP client with env-driven host, `post_event`, `post_batch` |
| `simulator/__main__.py` | Interactive CLI — `python -m simulator` |
| `simulator/scenarios/*.py` | Per-scenario shims (thin re-exports from event_generator) |
| `simulator/README.md` | Setup guide and scenario table |
| `.env.example` | Updated CORS_ORIGINS example for LAN IP ranges |
| `docs/phase-13.md` | This document |
