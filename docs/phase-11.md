# Phase 11 — React SOC Dashboard (Laptop 3)

Real-time analyst interface running on Laptop 3. Connects to Laptop 2's FastAPI engine via REST and WebSocket. All statistics, incidents, and telemetry are fetched live from the backend — zero hard-coded data.

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 18 + TypeScript via Vite |
| Styling | Vanilla CSS design system (no Tailwind) |
| Icons | Lucide React |
| Fonts | Inter + JetBrains Mono (Google Fonts) |
| State | React hooks (`useState`, `useEffect`, `useCallback`) |
| HTTP | Fetch API (`src/services/api.ts`) |
| WebSocket | Native WS with auto-reconnect (`src/services/websocket.ts`) |

## Pages

| Route (tab) | Page | Description |
|-------------|------|-------------|
| `overview` | OverviewPage | Live metric cards, active incidents table, telemetry stream terminal |
| `events` | LiveEventsPage | Full event table with filter, pause, and test-event injector |
| `incidents` | IncidentsPage | Sortable/filterable incident portfolio with inline status controls |
| `investigation` | InvestigationPage | Deep-dive: risk formula, timeline, evidence logs, analyst notes |
| `analytics` | AnalyticsPage | Severity distribution + interactive risk formula calibration |
| `explorer` | LogExplorerPage | Historical SQLite query + parser sandbox (CEF/JSON/syslog) |
| `status` | SystemStatusPage | Three-laptop topology map + subsystem health matrix |

## Running (Laptop 3)

```powershell
cd LogShield\frontend
npm install
npm run dev        # Dev server: http://localhost:5173
```

For cross-machine (Laptop 3 connecting to Laptop 2):

```powershell
# Set the backend host in .env before starting:
echo "VITE_LOGSHIELD_API=http://192.168.1.20:8000" > .env
npm run dev
```

## Building (Production Bundle)

```powershell
npm run build
# Output: dist/ — serve with any static file server
```

## What was created

| Path | Role |
|------|------|
| `frontend/src/App.tsx` | Root layout: sidebar + header + page router |
| `frontend/src/components/Header.tsx` | Live UTC clock, backend host badge, sync button |
| `frontend/src/components/Sidebar.tsx` | Navigation with WS status indicator |
| `frontend/src/components/RiskGauge.tsx` | Animated SVG risk gauge (sm/md/lg sizes) |
| `frontend/src/pages/OverviewPage.tsx` | SOC command center with telemetry cards |
| `frontend/src/pages/LiveEventsPage.tsx` | Real-time event stream table + injector |
| `frontend/src/pages/IncidentsPage.tsx` | Incident portfolio with inline triage |
| `frontend/src/pages/InvestigationPage.tsx` | Full incident deep-dive page |
| `frontend/src/pages/AnalyticsPage.tsx` | Risk model calibration simulator |
| `frontend/src/pages/LogExplorerPage.tsx` | Log query + parser sandbox |
| `frontend/src/pages/SystemStatusPage.tsx` | Health matrix + topology map |
| `frontend/src/services/api.ts` | REST client for all backend endpoints |
| `frontend/src/services/websocket.ts` | WS client with reconnect + fan-out subscriptions |
| `frontend/src/hooks/useSOCData.ts` | Composite hook: REST + WS live updates |
| `frontend/src/hooks/useWebSocket.ts` | WS status + message subscription hook |
| `frontend/src/types/index.ts` | TypeScript contracts mirroring backend schemas |
| `frontend/src/index.css` | Full design system (dark cyber theme, 700 lines) |

## Build Verification

```powershell
npm run build
# ✓ built in 1.45s  — 233 kB (63 kB gzip)
# Zero TypeScript errors
```
