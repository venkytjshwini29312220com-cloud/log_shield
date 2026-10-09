"""Correlation engine for LogShield (Phase 7).

Correlates related events and alerts within a configurable sliding window
(LOGSHIELD_CORRELATION_WINDOW_SECONDS, default 300s) across join keys:
  - user
  - source_ip
  - destination_ip
  - resource
  - multi-stage kill chain (auth → access → network)
Reconstructs unified incidents with auto timelines, risk scores, explanations, and recommendations.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.orm import Alert, Event, Incident, IncidentEvent
from app.risk import default_risk_engine
from app.websocket import ws_manager


def generate_next_incident_ids(session: Session, count: int = 1) -> list[str]:
    """Generate sequential, collision-free incident identifiers (e.g. INC-1001)."""
    stmt = select(Incident.incident_id).where(Incident.incident_id.like("INC-%"))
    existing_ids = session.scalars(stmt).all()

    max_num = 1000
    for iid in existing_ids:
        suffix = iid[4:]
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))

    allocated: list[str] = []
    current = max_num
    for _ in range(count):
        current += 1
        candidate = f"INC-{current:04d}"
        while session.get(Incident, candidate) is not None:
            current += 1
            candidate = f"INC-{current:04d}"
        allocated.append(candidate)
    return allocated


def _to_utc(dt: datetime | None) -> datetime | None:
    """Normalize datetime to UTC timezone-aware for safe comparisons."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class CorrelationEngine:
    """Groups related events and detection notices into coherent security incidents."""

    OPEN_STATUSES = ("NEW", "INVESTIGATING", "CONTAINED")

    def __init__(self, window_seconds: int = 300) -> None:
        self.window_seconds = window_seconds

    def find_matching_incident(
        self,
        session: Session,
        event: Event,
        window_seconds: int | None = None,
    ) -> Incident | None:
        """Find an active open incident sharing join keys within the correlation time window."""
        win = window_seconds if window_seconds is not None else self.window_seconds
        event_ts = _to_utc(event.timestamp) or datetime.now(timezone.utc)
        window_start = event_ts - timedelta(seconds=win)

        # 1. Fetch candidate open incidents active within the window
        all_open = list(
            session.scalars(
                select(Incident)
                .where(Incident.status.in_(self.OPEN_STATUSES))
                .order_by(Incident.last_seen.desc())
            ).all()
        )

        candidates = [
            inc
            for inc in all_open
            if inc.last_seen is not None and _to_utc(inc.last_seen) >= window_start
        ]

        if not candidates:
            return None

        # 2. Check direct join keys
        for inc in candidates:
            if event.user and inc.affected_user and event.user.lower() == inc.affected_user.lower():
                return inc
            if event.source_ip and inc.source_ip and event.source_ip == inc.source_ip:
                return inc
            if event.resource and inc.resource and event.resource.lower() == inc.resource.lower():
                return inc

        # 3. Check indirect join keys (via events linked to the incident)
        for inc in candidates:
            linked_stmt = (
                select(Event)
                .join(IncidentEvent, IncidentEvent.event_id == Event.event_id)
                .where(IncidentEvent.incident_id == inc.incident_id)
            )
            linked_events = session.scalars(linked_stmt).all()
            for linked in linked_events:
                if event.user and linked.user and event.user.lower() == linked.user.lower():
                    return inc
                if event.source_ip and linked.source_ip and event.source_ip == linked.source_ip:
                    return inc
                if event.destination_ip and linked.destination_ip and event.destination_ip == linked.destination_ip:
                    return inc
                if event.source_ip and linked.destination_ip and event.source_ip == linked.destination_ip:
                    return inc

        return None

    def _assess_incident_stages_and_risk(
        self,
        session: Session,
        incident: Incident,
    ) -> tuple[str, int, str, str, str, dict[str, Any]]:
        """Evaluate correlated events using RiskEngine to determine lifecycle stages, risk, explanation, and response."""
        return default_risk_engine.calculate_incident_risk(session, incident)

    def correlate_event(
        self,
        session: Session,
        event: Event,
        alerts: list[Alert] | None = None,
    ) -> Incident | None:
        """Correlate newly ingested event and its alerts into an open or new Incident."""
        alerts = alerts or []
        now = datetime.now(timezone.utc)

        # 1. Search for existing open incident within window
        incident = self.find_matching_incident(session, event)

        if incident is not None:
            # Capture pre-update risk and severity state
            old_score = incident.risk_score
            old_sev = incident.severity

            # Attach to existing open incident
            existing_link = session.scalar(
                select(IncidentEvent).where(
                    IncidentEvent.incident_id == incident.incident_id,
                    IncidentEvent.event_id == event.event_id,
                )
            )
            if existing_link is None:
                max_seq = session.scalar(
                    select(func.max(IncidentEvent.sequence)).where(
                        IncidentEvent.incident_id == incident.incident_id
                    )
                ) or 0
                link = IncidentEvent(
                    incident_id=incident.incident_id,
                    event_id=event.event_id,
                    sequence=int(max_seq) + 1,
                )
                session.add(link)

            # Update temporal and entity bounds
            ev_ts = _to_utc(event.timestamp)
            inc_first = _to_utc(incident.first_seen)
            inc_last = _to_utc(incident.last_seen)

            if inc_first is None or (ev_ts is not None and ev_ts < inc_first):
                incident.first_seen = ev_ts
            if inc_last is None or (ev_ts is not None and ev_ts > inc_last):
                incident.last_seen = ev_ts
            if not incident.affected_user and event.user:
                incident.affected_user = event.user
            if not incident.source_ip and event.source_ip:
                incident.source_ip = event.source_ip
            if not incident.resource and event.resource:
                incident.resource = event.resource

            # Associate alerts with this incident
            for alert in alerts:
                alert.incident_id = incident.incident_id

            session.flush()

            # Recompute stages, severity, and explainable risk score
            sev, score, summary, expl, reco, bdown = self._assess_incident_stages_and_risk(session, incident)
            incident.severity = sev
            incident.risk_score = score
            incident.summary = summary
            incident.explanation = expl
            incident.recommendation = reco
            incident.risk_breakdown = bdown
            incident.updated_at = now

            session.flush()

            # Phase 10: Broadcast updated incident and risk changes
            ws_manager.broadcast_incident_updated(incident)
            if old_score != incident.risk_score or old_sev != incident.severity:
                ws_manager.broadcast_risk_changed(incident, previous_score=old_score)

            return incident

        # 2. Check if event warrants a new incident
        is_suspicious_event = (
            bool(alerts)
            or (event.action or "").lower() in (
                "login_failed",
                "access_denied",
                "unauthorized",
                "port_scan",
                "outbound_scan",
                "sudo_execution",
            )
            or (event.status or "").lower() in ("failure", "denied")
        )

        if not is_suspicious_event:
            return None

        # Open new incident
        inc_id = generate_next_incident_ids(session, count=1)[0]
        initial_severity = "MEDIUM"
        initial_risk = 45
        if alerts:
            if any(a.severity == "CRITICAL" for a in alerts):
                initial_severity = "CRITICAL"
                initial_risk = 85
            elif any(a.severity == "HIGH" for a in alerts):
                initial_severity = "HIGH"
                initial_risk = 70

        ev_ts = _to_utc(event.timestamp)
        incident = Incident(
            incident_id=inc_id,
            created_at=now,
            updated_at=now,
            first_seen=ev_ts,
            last_seen=ev_ts,
            severity=initial_severity,
            risk_score=initial_risk,
            status="NEW",
            summary=f"Security event: {event.action} for user '{event.user or 'unknown'}'",
            explanation=f"Initial detection of suspicious event: {event.action} on resource {event.resource}.",
            recommendation="Monitor user and source IP for follow-on actions.",
            affected_user=event.user,
            source_ip=event.source_ip,
            resource=event.resource,
            risk_breakdown={"initial_event": event.event_id, "stages_count": 1},
        )
        session.add(incident)
        session.flush()

        # Link event
        link = IncidentEvent(incident_id=inc_id, event_id=event.event_id, sequence=1)
        session.add(link)

        # Link alerts
        for alert in alerts:
            alert.incident_id = inc_id

        session.flush()

        # Re-assess stages
        sev, score, summary, expl, reco, bdown = self._assess_incident_stages_and_risk(session, incident)
        incident.severity = sev
        incident.risk_score = score
        incident.summary = summary
        incident.explanation = expl
        incident.recommendation = reco
        incident.risk_breakdown = bdown

        session.flush()

        # Phase 10: Broadcast newly created incident and initial risk score
        ws_manager.broadcast_incident_created(incident)
        ws_manager.broadcast_risk_changed(incident, previous_score=None)

        return incident


# Global singleton instance
default_correlation_engine = CorrelationEngine()
