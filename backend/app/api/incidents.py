"""Incident management and analyst workflow API router (Phase 9).

Supports SOC analyst triage: status transitions (NEW -> INVESTIGATING -> CONTAINED -> RESOLVED -> FALSE_POSITIVE),
investigation notes, audit trails, and unified chronological timeline reconstruction.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.orm import Alert, Event, Incident, IncidentEvent
from app.websocket import ws_manager
from app.models.schemas import (
    AlertRead,
    EventRead,
    IncidentDetail,
    IncidentListResponse,
    IncidentNoteCreate,
    IncidentRead,
    IncidentTimelineResponse,
    IncidentUpdate,
    TimelineItem,
)

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

VALID_STATUSES = {"NEW", "INVESTIGATING", "CONTAINED", "RESOLVED", "FALSE_POSITIVE"}


def _get_incident_detail(db: Session, incident: Incident) -> IncidentDetail:
    """Helper to populate IncidentDetail with linked events and alerts."""
    events_stmt = (
        select(Event)
        .join(IncidentEvent, IncidentEvent.event_id == Event.event_id)
        .where(IncidentEvent.incident_id == incident.incident_id)
        .order_by(IncidentEvent.sequence.asc(), Event.timestamp.asc())
    )
    events = list(db.scalars(events_stmt).all())

    alerts_stmt = (
        select(Alert)
        .where(Alert.incident_id == incident.incident_id)
        .order_by(Alert.created_at.asc())
    )
    alerts = list(db.scalars(alerts_stmt).all())

    detail = IncidentDetail.model_validate(incident)
    detail.events = [EventRead.model_validate(e) for e in events]
    detail.alerts = [AlertRead.model_validate(a) for a in alerts]
    return detail


@router.get("", response_model=IncidentListResponse)
def list_incidents(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = None,
    user: str | None = None,
    source_ip: str | None = None,
    db: Session = Depends(get_db),
) -> IncidentListResponse:
    query = select(Incident)
    count_query = select(func.count()).select_from(Incident)

    if status_filter:
        query = query.where(Incident.status == status_filter)
        count_query = count_query.where(Incident.status == status_filter)
    if severity:
        query = query.where(Incident.severity == severity)
        count_query = count_query.where(Incident.severity == severity)
    if user:
        query = query.where(Incident.affected_user == user)
        count_query = count_query.where(Incident.affected_user == user)
    if source_ip:
        query = query.where(Incident.source_ip == source_ip)
        count_query = count_query.where(Incident.source_ip == source_ip)

    total = db.scalar(count_query) or 0
    items = db.scalars(query.order_by(Incident.created_at.desc()).offset(offset).limit(limit)).all()

    return IncidentListResponse(
        items=[IncidentRead.model_validate(item) for item in items],
        total=int(total),
        limit=limit,
        offset=offset,
    )


@router.get("/{incident_id}", response_model=IncidentDetail)
def get_incident(incident_id: str, db: Session = Depends(get_db)) -> IncidentDetail:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found",
        )
    return _get_incident_detail(db, incident)


@router.patch("/{incident_id}", response_model=IncidentDetail)
async def patch_incident(
    incident_id: str,
    update: IncidentUpdate,
    db: Session = Depends(get_db),
) -> IncidentDetail:
    """Update incident analyst workflow status, notes, and assignee."""
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found",
        )

    now = datetime.now(timezone.utc)
    old_status = incident.status
    breakdown = dict(incident.risk_breakdown or {})
    analyst_history = list(breakdown.get("analyst_history", []))
    notes_list = list(breakdown.get("notes", []))

    if update.status is not None:
        if update.status not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status '{update.status}'. Allowed statuses: {', '.join(sorted(VALID_STATUSES))}",
            )
        incident.status = update.status

    if update.notes:
        note_entry = {
            "timestamp": now.isoformat(),
            "analyst": update.analyst or "analyst",
            "note": update.notes,
        }
        notes_list.append(note_entry)

    if update.assigned_to:
        breakdown["assigned_to"] = update.assigned_to

    # Record audit trail entry
    if (update.status is not None and update.status != old_status) or update.notes:
        audit_entry = {
            "timestamp": now.isoformat(),
            "analyst": update.analyst or "analyst",
            "old_status": old_status,
            "new_status": incident.status,
            "note": update.notes,
        }
        analyst_history.append(audit_entry)

    breakdown["analyst_history"] = analyst_history
    breakdown["notes"] = notes_list
    incident.risk_breakdown = breakdown
    incident.updated_at = now

    db.flush()

    # Phase 10: Broadcast updated incident
    ws_manager.broadcast_incident_updated(incident)
    await asyncio.sleep(0)

    return _get_incident_detail(db, incident)


@router.post("/{incident_id}/notes", response_model=IncidentDetail)
async def add_incident_note(
    incident_id: str,
    payload: IncidentNoteCreate,
    db: Session = Depends(get_db),
) -> IncidentDetail:
    """Append an analyst note to the incident."""
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found",
        )

    now = datetime.now(timezone.utc)
    breakdown = dict(incident.risk_breakdown or {})
    notes_list = list(breakdown.get("notes", []))

    note_entry = {
        "timestamp": now.isoformat(),
        "analyst": payload.analyst or "analyst",
        "note": payload.note,
    }
    notes_list.append(note_entry)

    analyst_history = list(breakdown.get("analyst_history", []))
    analyst_history.append({
        "timestamp": now.isoformat(),
        "analyst": payload.analyst or "analyst",
        "action": "NOTE_ADDED",
        "note": payload.note,
    })

    breakdown["notes"] = notes_list
    breakdown["analyst_history"] = analyst_history
    incident.risk_breakdown = breakdown
    incident.updated_at = now

    db.flush()

    # Phase 10: Broadcast updated incident
    ws_manager.broadcast_incident_updated(incident)
    await asyncio.sleep(0)

    return _get_incident_detail(db, incident)


@router.get("/{incident_id}/timeline", response_model=IncidentTimelineResponse)
def get_incident_timeline(
    incident_id: str,
    db: Session = Depends(get_db),
) -> IncidentTimelineResponse:
    """Return unified chronological sequence of events, detection alerts, and audit actions."""
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found",
        )

    timeline_items: list[TimelineItem] = []

    # 1. Correlated events
    events_stmt = (
        select(Event)
        .join(IncidentEvent, IncidentEvent.event_id == Event.event_id)
        .where(IncidentEvent.incident_id == incident_id)
        .order_by(Event.timestamp.asc())
    )
    events = list(db.scalars(events_stmt).all())
    for e in events:
        ts = e.timestamp if e.timestamp.tzinfo else e.timestamp.replace(tzinfo=timezone.utc)
        timeline_items.append(
            TimelineItem(
                timestamp=ts,
                item_type="event",
                title=f"{e.event_type.upper()}: {e.action}",
                details={
                    "event_id": e.event_id,
                    "user": e.user,
                    "source_ip": e.source_ip,
                    "resource": e.resource,
                    "status": e.status,
                },
            )
        )

    # 2. Associated alerts
    alerts_stmt = select(Alert).where(Alert.incident_id == incident_id).order_by(Alert.created_at.asc())
    alerts = list(db.scalars(alerts_stmt).all())
    for a in alerts:
        ts = a.created_at if a.created_at.tzinfo else a.created_at.replace(tzinfo=timezone.utc)
        timeline_items.append(
            TimelineItem(
                timestamp=ts,
                item_type="alert",
                title=f"ALERT ({a.severity}): {a.title}",
                details={
                    "alert_id": a.alert_id,
                    "source": a.source,
                    "severity": a.severity,
                    "message": a.message,
                },
            )
        )

    # 3. Analyst audit trail
    breakdown = incident.risk_breakdown or {}
    analyst_history = breakdown.get("analyst_history", [])
    for entry in analyst_history:
        ts_str = entry.get("timestamp")
        try:
            ts = datetime.fromisoformat(ts_str) if ts_str else incident.updated_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except Exception:
            ts = incident.updated_at

        note_txt = f" - '{entry['note']}'" if entry.get("note") else ""
        title = f"AUDIT: Status changed to {entry.get('new_status')}{note_txt}" if "new_status" in entry else f"AUDIT: {entry.get('action', 'ACTION')}{note_txt}"

        timeline_items.append(
            TimelineItem(
                timestamp=ts,
                item_type="audit",
                title=title,
                details=entry,
            )
        )

    # Sort strictly chronologically
    timeline_items.sort(key=lambda item: item.timestamp)

    return IncidentTimelineResponse(
        incident_id=incident_id,
        items=timeline_items,
        total=len(timeline_items),
    )
