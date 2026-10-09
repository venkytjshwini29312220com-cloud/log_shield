"""Connection manager for /ws/events real-time fan-out (Phase 10).

Provides WebSocket connection lifecycle management, graceful disconnect handling,
and synchronous/asynchronous fan-out of security telemetry:
  - event.created
  - alert.created
  - incident.created
  - incident.updated
  - risk.changed
  - system.status
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any

from fastapi import WebSocket

from app.models.orm import Alert, Event, Incident
from app.models.schemas import AlertRead, EventRead, IncidentRead

logger = logging.getLogger("logshield.websocket")

SUPPORTED_EVENT_TYPES = [
    "event.created",
    "alert.created",
    "incident.created",
    "incident.updated",
    "risk.changed",
    "system.status",
    "pong",
]


def _to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts real-time security telemetry."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()
        self._main_loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._main_loop = loop

    @property
    def active_count(self) -> int:
        return len(self.active_connections)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept incoming connection and register in active pool."""
        await websocket.accept()
        try:
            self._main_loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        async with self._lock:
            if websocket not in self.active_connections:
                self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active: {self.active_count}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove connection from active pool cleanly."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active: {self.active_count}")

    async def broadcast(self, message: dict[str, Any]) -> int:
        """Broadcast message to all active WebSocket clients.

        Prunes dead connections on failure without interrupting remaining clients.
        Returns the count of successfully sent messages.
        """
        if not self.active_connections:
            return 0

        async with self._lock:
            clients = list(self.active_connections)

        delivered = 0
        dead_clients: list[WebSocket] = []

        for ws in clients:
            try:
                await ws.send_json(message)
                delivered += 1
            except Exception as exc:
                logger.warning(f"Failed to transmit WebSocket frame: {exc}. Dropping connection.")
                dead_clients.append(ws)

        if dead_clients:
            async with self._lock:
                for ws in dead_clients:
                    if ws in self.active_connections:
                        self.active_connections.remove(ws)

        return delivered

    def broadcast_sync(self, message: dict[str, Any]) -> None:
        """Safely schedule broadcast from synchronous functions or threadpool workers."""
        if not self.active_connections:
            return

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(message))
        except RuntimeError:
            if self._main_loop and self._main_loop.is_running():
                try:
                    fut = asyncio.run_coroutine_threadsafe(self.broadcast(message), self._main_loop)
                    fut.result(timeout=2.0)
                except Exception as exc:
                    logger.debug(f"Threadsafe broadcast error: {exc}")

    def _wrap_envelope(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }

    def broadcast_event(self, event: Event | EventRead | dict[str, Any]) -> None:
        """Fan-out 'event.created' telemetry."""
        if not self.active_connections:
            return

        if isinstance(event, Event):
            payload = {
                "event_id": event.event_id,
                "timestamp": _to_iso(event.timestamp),
                "source_ip": event.source_ip,
                "destination_ip": event.destination_ip,
                "user": event.user,
                "event_type": event.event_type,
                "action": event.action,
                "status": event.status,
                "resource": event.resource,
                "protocol": event.protocol,
                "source_device": event.source_device,
                "metadata": event.metadata_json or {},
                "ingested_at": _to_iso(event.ingested_at),
            }
        elif isinstance(event, EventRead):
            payload = event.model_dump(mode="json")
        elif isinstance(event, dict):
            payload = dict(event)
        else:
            payload = {"event_id": getattr(event, "event_id", "unknown")}

        self.broadcast_sync(self._wrap_envelope("event.created", payload))

    def broadcast_alert(self, alert: Alert | AlertRead | dict[str, Any]) -> None:
        """Fan-out 'alert.created' telemetry."""
        if not self.active_connections:
            return

        if isinstance(alert, Alert):
            payload = {
                "alert_id": alert.alert_id,
                "created_at": _to_iso(alert.created_at),
                "source": alert.source,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "event_id": alert.event_id,
                "incident_id": alert.incident_id,
                "extras": (alert.extras if hasattr(alert, "extras") else getattr(alert, "extras_json", {})) or {},
            }
        elif isinstance(alert, AlertRead):
            payload = alert.model_dump(mode="json")
        elif isinstance(alert, dict):
            payload = dict(alert)
        else:
            payload = {"alert_id": getattr(alert, "alert_id", "unknown")}

        self.broadcast_sync(self._wrap_envelope("alert.created", payload))

    def broadcast_incident_created(self, incident: Incident | IncidentRead | dict[str, Any]) -> None:
        """Fan-out 'incident.created' telemetry."""
        if not self.active_connections:
            return

        if isinstance(incident, Incident):
            payload = {
                "incident_id": incident.incident_id,
                "severity": incident.severity,
                "risk_score": incident.risk_score,
                "status": incident.status,
                "summary": incident.summary,
                "explanation": incident.explanation,
                "recommendation": incident.recommendation,
                "affected_user": incident.affected_user,
                "source_ip": incident.source_ip,
                "resource": incident.resource,
                "first_seen": _to_iso(incident.first_seen),
                "last_seen": _to_iso(incident.last_seen),
                "created_at": _to_iso(incident.created_at),
                "updated_at": _to_iso(incident.updated_at),
                "risk_breakdown": incident.risk_breakdown or {},
            }
        elif isinstance(incident, IncidentRead):
            payload = incident.model_dump(mode="json")
        elif isinstance(incident, dict):
            payload = dict(incident)
        else:
            payload = {"incident_id": getattr(incident, "incident_id", "unknown")}

        self.broadcast_sync(self._wrap_envelope("incident.created", payload))

    def broadcast_incident_updated(self, incident: Incident | IncidentRead | dict[str, Any]) -> None:
        """Fan-out 'incident.updated' telemetry."""
        if not self.active_connections:
            return

        if isinstance(incident, Incident):
            payload = {
                "incident_id": incident.incident_id,
                "severity": incident.severity,
                "risk_score": incident.risk_score,
                "status": incident.status,
                "summary": incident.summary,
                "explanation": incident.explanation,
                "recommendation": incident.recommendation,
                "affected_user": incident.affected_user,
                "source_ip": incident.source_ip,
                "resource": incident.resource,
                "first_seen": _to_iso(incident.first_seen),
                "last_seen": _to_iso(incident.last_seen),
                "created_at": _to_iso(incident.created_at),
                "updated_at": _to_iso(incident.updated_at),
                "risk_breakdown": incident.risk_breakdown or {},
            }
        elif isinstance(incident, IncidentRead):
            payload = incident.model_dump(mode="json")
        elif isinstance(incident, dict):
            payload = dict(incident)
        else:
            payload = {"incident_id": getattr(incident, "incident_id", "unknown")}

        self.broadcast_sync(self._wrap_envelope("incident.updated", payload))

    def broadcast_risk_changed(
        self,
        incident: Incident | dict[str, Any],
        previous_score: int | None = None,
    ) -> None:
        """Fan-out 'risk.changed' score update telemetry."""
        if not self.active_connections:
            return

        if isinstance(incident, Incident):
            payload = {
                "incident_id": incident.incident_id,
                "risk_score": incident.risk_score,
                "previous_risk_score": previous_score,
                "severity": incident.severity,
                "risk_breakdown": incident.risk_breakdown or {},
            }
        elif isinstance(incident, dict):
            payload = {
                "incident_id": incident.get("incident_id"),
                "risk_score": incident.get("risk_score", 0),
                "previous_risk_score": previous_score,
                "severity": incident.get("severity", "LOW"),
                "risk_breakdown": incident.get("risk_breakdown", {}),
            }
        else:
            payload = {"incident_id": getattr(incident, "incident_id", "unknown")}

        self.broadcast_sync(self._wrap_envelope("risk.changed", payload))

    def broadcast_system_status(self, payload: dict[str, Any] | None = None) -> None:
        """Fan-out 'system.status' heartbeat / component health."""
        if not self.active_connections:
            return
        status_payload = payload or self.get_status_payload()
        self.broadcast_sync(self._wrap_envelope("system.status", status_payload))

    def get_status_payload(self) -> dict[str, Any]:
        return {
            "system": "ONLINE",
            "ai_engine": "ONLINE",
            "log_collector": "ONLINE",
            "websocket": "ONLINE",
            "active_connections": self.active_count,
            "phase": 10,
        }


# Global singleton manager instance
ws_manager = ConnectionManager()
