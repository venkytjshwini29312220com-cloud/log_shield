"""Event ingestion service for LogShield (Phase 4).

Orchestrates parsing, schema normalization, unique ID assignment,
conflict detection, and persistence to SQLite.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.correlation import default_correlation_engine
from app.detection import default_ml_detector, default_rule_engine
from app.models.orm import Event
from app.models.schemas import EventBatchResponse, EventRead
from app.services.parser import LogParser
from app.websocket import ws_manager


def generate_next_event_ids(session: Session, count: int = 1) -> list[str]:
    """Generate sequential, collision-free event identifiers (e.g. EVT-0001)."""
    stmt = select(Event.event_id).where(Event.event_id.like("EVT-%"))
    existing_ids = session.scalars(stmt).all()

    max_num = 0
    for eid in existing_ids:
        suffix = eid[4:]
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))

    allocated: list[str] = []
    current = max_num
    for _ in range(count):
        current += 1
        candidate = f"EVT-{current:04d}"
        while session.get(Event, candidate) is not None:
            current += 1
            candidate = f"EVT-{current:04d}"
        allocated.append(candidate)
    return allocated


class IngestionService:
    """Service handling log parsing, validation, and storage into SQLite."""

    @classmethod
    def normalize_and_validate(cls, raw_data: Any) -> dict[str, Any]:
        """Normalize raw log or dictionary payload and enforce schema invariants."""
        try:
            normalized = LogParser.parse(raw_data)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to parse event: {exc}",
            ) from exc

        event_type = normalized.get("event_type")
        action = normalized.get("action")

        if not event_type or not action:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Event validation failed: 'event_type' and 'action' are required fields "
                    "or must be extractable from log payload."
                ),
            )

        return normalized

    @classmethod
    def ingest_single(cls, session: Session, raw_event: Any) -> EventRead:
        """Parse, validate, and persist a single event."""
        normalized = cls.normalize_and_validate(raw_event)

        event_id = normalized.get("event_id")
        if event_id:
            existing = session.get(Event, event_id)
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Event with id '{event_id}' already exists",
                )
        else:
            event_id = generate_next_event_ids(session, count=1)[0]

        now = datetime.now(timezone.utc)
        orm_event = Event(
            event_id=event_id,
            timestamp=normalized["timestamp"],
            source_ip=normalized.get("source_ip"),
            destination_ip=normalized.get("destination_ip"),
            user=normalized.get("user"),
            event_type=normalized["event_type"],
            action=normalized["action"],
            status=normalized.get("status"),
            resource=normalized.get("resource"),
            protocol=normalized.get("protocol"),
            source_device=normalized.get("source_device"),
            metadata_json=normalized.get("metadata", {}),
            raw=normalized.get("raw"),
            ingested_at=now,
        )

        session.add(orm_event)
        session.flush()

        # Phase 10: Broadcast newly stored event
        ws_manager.broadcast_event(orm_event)

        # Phase 5: Evaluate detection rules
        rule_alerts = default_rule_engine.evaluate_event(session, orm_event)

        # Phase 6: Evaluate Isolation Forest anomaly detection
        _ml_score, ml_alert = default_ml_detector.evaluate_event(session, orm_event)

        # Phase 10: Broadcast alerts
        for alert in rule_alerts:
            ws_manager.broadcast_alert(alert)
        if ml_alert:
            ws_manager.broadcast_alert(ml_alert)

        # Phase 7: Correlate events & alerts into Incidents
        all_alerts = list(rule_alerts)
        if ml_alert:
            all_alerts.append(ml_alert)
        default_correlation_engine.correlate_event(session, orm_event, all_alerts)

        return EventRead.model_validate(orm_event)

    @classmethod
    def ingest_batch(cls, session: Session, raw_events: list[Any]) -> EventBatchResponse:
        """Parse, validate, and atomically persist a batch of events."""
        if not raw_events:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Batch cannot be empty. At least one event is required.",
            )

        # 1. Parse and validate all items
        normalized_list: list[dict[str, Any]] = []
        needed_auto_ids = 0

        for idx, item in enumerate(raw_events):
            try:
                norm = cls.normalize_and_validate(item)
            except HTTPException as exc:
                raise HTTPException(
                    status_code=exc.status_code,
                    detail=f"Error in batch item [{idx}]: {exc.detail}",
                ) from exc
            normalized_list.append(norm)
            if not norm.get("event_id"):
                needed_auto_ids += 1

        # 2. Check explicit ID uniqueness / conflicts
        seen_batch_ids: set[str] = set()
        for idx, norm in enumerate(normalized_list):
            eid = norm.get("event_id")
            if eid:
                if eid in seen_batch_ids:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Duplicate event_id '{eid}' within the batch",
                    )
                seen_batch_ids.add(eid)
                if session.get(Event, eid) is not None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Event with id '{eid}' already exists in database",
                    )

        # 3. Allocate automatic sequential IDs
        auto_ids = generate_next_event_ids(session, count=needed_auto_ids) if needed_auto_ids > 0 else []
        auto_id_iter = iter(auto_ids)

        now = datetime.now(timezone.utc)
        stored_reads: list[EventRead] = []

        stored_events: list[Event] = []
        for norm in normalized_list:
            eid = norm.get("event_id") or next(auto_id_iter)
            orm_event = Event(
                event_id=eid,
                timestamp=norm["timestamp"],
                source_ip=norm.get("source_ip"),
                destination_ip=norm.get("destination_ip"),
                user=norm.get("user"),
                event_type=norm["event_type"],
                action=norm["action"],
                status=norm.get("status"),
                resource=norm.get("resource"),
                protocol=norm.get("protocol"),
                source_device=norm.get("source_device"),
                metadata_json=norm.get("metadata", {}),
                raw=norm.get("raw"),
                ingested_at=now,
            )
            session.add(orm_event)
            session.flush()
            stored_events.append(orm_event)
            stored_reads.append(EventRead.model_validate(orm_event))

        # Phase 10: Broadcast stored events
        for evt in stored_events:
            ws_manager.broadcast_event(evt)

        # Phase 5, 6, 7: Detection rules, ML anomaly detection, and correlation
        for evt in stored_events:
            rule_alerts = default_rule_engine.evaluate_event(session, evt)
            _ml_score, ml_alert = default_ml_detector.evaluate_event(session, evt)
            for alert in rule_alerts:
                ws_manager.broadcast_alert(alert)
            if ml_alert:
                ws_manager.broadcast_alert(ml_alert)

            all_alerts = list(rule_alerts)
            if ml_alert:
                all_alerts.append(ml_alert)
            default_correlation_engine.correlate_event(session, evt, all_alerts)

        return EventBatchResponse(events=stored_reads, count=len(stored_reads))

    @classmethod
    def ingest_text(cls, session: Session, text: str) -> EventRead | EventBatchResponse:
        """Parse raw text (single or multi-line logs) and ingest."""
        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        if not lines:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Log text cannot be empty",
            )
        if len(lines) == 1:
            return cls.ingest_single(session, lines[0])
        return cls.ingest_batch(session, lines)
