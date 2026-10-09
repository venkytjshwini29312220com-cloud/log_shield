# Phase 12 — Incident Investigation Page

Dedicated deep-investigation workspace that an SOC analyst opens when triaging a correlated incident. Integrates all Phase 7–9 backend capabilities into one unified analyst view.

## Features

### Incident Header Bar
- `incident_id`, `severity` badge, `status` badge
- Animated `RiskGauge` (0–100) showing composite risk score
- Quick-status dropdown (`NEW → INVESTIGATING → CONTAINED → RESOLVED → FALSE_POSITIVE`)

### Intrusion Explanation & Defensive Recommendation
Two side-by-side panels showing the engine's natural-language analysis and recommended containment actions. Quick-action buttons:
- **Isolate / Contain** — one-click `PATCH` to `CONTAINED`
- **Mark Resolved** — one-click `PATCH` to `RESOLVED`

### Explainable Risk Formula Breakdown
Four component score cards with weighted contribution points:
- Rule Detection (30%) — raw rule engine match score
- Isolation Forest ML (30%) — anomaly score from unsupervised model
- Kill-Chain Correlation (25%) — multi-stage correlation depth
- Behavioral Context (15%) — entity enrichment signals

### Chronological Timeline Reconstruction
Unified `GET /api/incidents/{id}/timeline` view merging:
- 🔵 **Event** frames (raw log ingestion)
- 🔴 **Alert** frames (rule + ML detection notices)
- 🟣 **Audit** frames (analyst status transitions + notes)

### Correlated Evidence Log Stream
Full table of all events correlated into the incident with event ID, timestamps, source IP, user, action, status, and resource.

### Analyst Notes & Audit Form
- Analyst handle input
- Free-text investigation findings textarea
- `POST /api/incidents/{id}/notes` submission
- Historical notes list with analyst attribution and timestamps

## What was created / updated

| Path | Role |
|------|------|
| `frontend/src/pages/InvestigationPage.tsx` | Full implementation (547 lines) |
| `frontend/src/services/api.ts` | `getIncidentTimeline`, `patchIncident`, `addIncidentNote` |
| `frontend/src/types/index.ts` | `TimelineItem`, `IncidentTimelineResponse`, `IncidentDetail` |
