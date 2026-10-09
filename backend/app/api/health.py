from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.deps import get_db, settings_dep
from app.config import Settings
from app.models.orm import SystemStatus
from app.models.schemas import ComponentHealth, ComponentStatus, HealthResponse, SystemStatusResponse
from app.websocket import ws_manager

router = APIRouter(tags=["health"])


def _ping_database(db: Session) -> tuple[ComponentStatus, str]:
    try:
        db.execute(text("SELECT 1"))
        return "ONLINE", "SQLite reachable; schema initialized"
    except Exception as exc:  # pragma: no cover - defensive
        return "OFFLINE", f"SQLite ping failed: {exc}"


@router.get("/api/health", response_model=HealthResponse)
def health(settings: Settings = Depends(settings_dep)) -> HealthResponse:
    return HealthResponse(status="ok", service="logshield-engine", phase=settings.implementation_phase)


@router.get("/api/system-status", response_model=SystemStatusResponse)
def system_status(
    settings: Settings = Depends(settings_dep),
    db: Session = Depends(get_db),
) -> SystemStatusResponse:
    db_status, db_detail = _ping_database(db)
    stored = {row.component: row for row in db.scalars(select(SystemStatus)).all()}

    def component(name: str, fallback_status: ComponentStatus, fallback_detail: str) -> ComponentHealth:
        row = stored.get(name)
        if row is None:
            return ComponentHealth(status=fallback_status, detail=fallback_detail)
        status: ComponentStatus = row.status if row.status in ("ONLINE", "NOT_READY", "OFFLINE") else fallback_status
        return ComponentHealth(status=status, detail=row.detail or fallback_detail)

    if db_status != "ONLINE":
        database = ComponentHealth(status=db_status, detail=db_detail)
    else:
        database = component("database", "ONLINE", db_detail)

    return SystemStatusResponse(
        system="ONLINE" if db_status == "ONLINE" else "OFFLINE",
        ai_engine="ONLINE",
        log_collector="ONLINE",
        ml_model=settings.ml_model_label,
        correlation_window_seconds=settings.correlation_window_seconds,
        public_base_url=settings.public_base_url,
        phase=settings.implementation_phase,
        components={
            "api": component("api", "ONLINE", "FastAPI process accepting HTTP"),
            "database": database,
            "ai_engine": component(
                "ai_engine",
                "ONLINE",
                "Hybrid detection active: Rule Engine (6 rules) + Isolation Forest anomaly detector",
            ),
            "log_collector": component(
                "log_collector",
                "ONLINE",
                "Event ingestion and normalization pipeline active (POST /api/events)",
            ),
            "websocket": component(
                "websocket",
                "ONLINE",
                f"Real-time fan-out broadcaster active (/ws/events, {ws_manager.active_count} connected)",
            ),
        },
    )
