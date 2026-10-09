"""FastAPI WebSocket endpoint and telemetry management routes (Phase 10)."""

from datetime import datetime, timezone
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.models.schemas import WebSocketBroadcastRequest, WebSocketStatusResponse
from app.websocket.manager import SUPPORTED_EVENT_TYPES, ws_manager

logger = logging.getLogger("logshield.websocket")

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/events")
async def websocket_events_endpoint(websocket: WebSocket) -> None:
    """Real-time security telemetry WebSocket endpoint for Laptop 3 SOC Dashboard.

    Transmits:
      - Initial 'system.status' welcome handshake
      - Continuous broadcasts: 'event.created', 'alert.created', 'incident.created',
        'incident.updated', 'risk.changed', 'system.status'
      - Responds to 'ping' heartbeats with 'pong'
    """
    await ws_manager.connect(websocket)
    try:
        # Transmit initial system.status handshake / telemetry welcome
        await websocket.send_json({
            "type": "system.status",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": ws_manager.get_status_payload(),
        })

        while True:
            # Keep connection open; process incoming client frames
            raw_text = await websocket.receive_text()
            cleaned = raw_text.strip()
            if cleaned == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {"status": "ok"},
                })
            else:
                try:
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, dict) and parsed.get("type") == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "payload": {"status": "ok"},
                        })
                except Exception:
                    pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.debug(f"WebSocket session terminated: {exc}")
        ws_manager.disconnect(websocket)


@router.get(
    "/api/websocket/status",
    response_model=WebSocketStatusResponse,
    summary="WebSocket subsystem status",
    description="Inspect active connected SOC dashboard clients and supported fan-out event types.",
)
def get_websocket_status() -> WebSocketStatusResponse:
    return WebSocketStatusResponse(
        status="ONLINE",
        active_connections=ws_manager.active_count,
        endpoint="/ws/events",
        supported_events=SUPPORTED_EVENT_TYPES,
    )


@router.post(
    "/api/websocket/broadcast",
    status_code=status.HTTP_200_OK,
    summary="Manual telemetry broadcast (testing / operations)",
)
async def post_broadcast_message(req: WebSocketBroadcastRequest) -> dict[str, Any]:
    delivered = await ws_manager.broadcast({
        "type": req.type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": req.payload,
    })
    return {
        "status": "delivered",
        "recipients": delivered,
        "type": req.type,
    }
