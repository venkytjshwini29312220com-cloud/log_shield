# LogShield

**Hackathon ID:** AI26CY03 — Log-Based Intrusion Detection

LogShield is a **prototype** SOC pipeline: it does not only list suspicious logs. It **correlates related events**, reconstructs **incidents**, scores **explainable risk**, and shows an **automatic timeline** to an analyst.

> Prototype AI: the Isolation Forest layer is a lightweight unsupervised detector trained on synthetic lab traffic. Scores are **risk scores (0–100)**, not attack probabilities.

## Three-laptop architecture

| Role | Machine | Responsibility |
|------|---------|----------------|
| Event simulator | Laptop 1 | Controlled synthetic logs and demo scenarios |
| AI engine | Laptop 2 | Ingest, detect, correlate, score, persist, WebSocket |
| SOC dashboard | Laptop 3 | Real-time analyst UI (all values from the API) |

Laptop 2 is the only server. Laptops 1 and 3 call it by configurable host (`LOGSHIELD_SERVER_HOST`). Nothing is hard-coded to `localhost` for cross-machine use.

```text
Laptop 1 (simulator)
        |  HTTP POST /api/events  (or WS)
        v
Laptop 2 (LogShield engine)
        |  parser → features → rules → ML → correlation → risk → incidents
        |  WebSocket /ws/events
        v
Laptop 3 (SOC dashboard)
```

## Monorepo layout

```text
LogShield/
├── backend/      # Laptop 2 — FastAPI engine (Phase 2+)
├── frontend/     # Laptop 3 — React SOC UI (Phase 11+)
├── simulator/    # Laptop 1 — safe scenario producer (later phases)
└── docs/         # Architecture, API contract, demo script
```

## Current status

**Phase 13 complete:** Three-laptop LAN network config, simulator CLI (scenarios A–F), and cross-machine CORS. Full pipeline: Laptop 1 (simulator) → Laptop 2 (AI engine) → Laptop 3 (React SOC dashboard).

| Phase | Scope | Status |
|-------|--------|--------|
| 1 | Architecture and folders | Done |
| 2 | FastAPI skeleton | Done |
| 3 | SQLite schema | Done |
| 4 | Log ingestion / parse / normalize | Done |
| 5 | Rule engine | Done |
| 6 | Isolation Forest anomaly detection | Done |
| 7 | Correlation engine | Done |
| 8 | Risk engine | Done |
| 9 | Incident management | Done |
| 10 | WebSocket fan-out | Done |
| 11 | React dashboard | Done |
| 12 | Incident investigation page | Done |
| 13 | Three-laptop network config & simulator | Done |
| 14 | Automated tests | Not started |
| 15 | Hackathon demo polish | Not started |

## Configuration

Copy `.env.example` to `.env` on each machine and set `LOGSHIELD_SERVER_HOST` to Laptop 2’s LAN IP.

## Safety

This is a **controlled lab**. The simulator only emits predefined synthetic events. The engine does not execute commands from logs, does not attack external systems, and does not auto-contain hosts.

## Docs

- [Architecture](docs/architecture.md)
- [API contract](docs/api.md)
- [Demo script](docs/demo.md)
- [Phase 1 notes](docs/phase-1.md)
- [Phase 2 notes](docs/phase-2.md)
- [Phase 3 notes](docs/phase-3.md)
- [Phase 4 notes](docs/phase-4.md)
- [Phase 5 notes](docs/phase-5.md)
- [Phase 6 notes](docs/phase-6.md)
- [Phase 7 notes](docs/phase-7.md)
- [Phase 8 notes](docs/phase-8.md)
- [Phase 9 notes](docs/phase-9.md)
- [Phase 10 notes](docs/phase-10.md)
- [Phase 11 notes](docs/phase-11.md)
- [Phase 12 notes](docs/phase-12.md)
- [Phase 13 notes](docs/phase-13.md)
