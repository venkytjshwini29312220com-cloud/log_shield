from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.orm import Alert, Event, Incident
from app.models.schemas import StatisticsResponse

router = APIRouter(tags=["statistics"])

_ACTIVE = ("NEW", "INVESTIGATING", "CONTAINED")


@router.get("/api/statistics", response_model=StatisticsResponse)
def statistics(db: Session = Depends(get_db)) -> StatisticsResponse:
    total_events = db.scalar(select(func.count()).select_from(Event)) or 0
    threats_detected = db.scalar(select(func.count()).select_from(Alert)) or 0
    active_incidents = db.scalar(
        select(func.count()).select_from(Incident).where(Incident.status.in_(_ACTIVE))
    ) or 0
    critical_incidents = db.scalar(
        select(func.count()).select_from(Incident).where(Incident.severity == "CRITICAL")
    ) or 0
    current_risk = db.scalar(
        select(func.max(Incident.risk_score)).where(Incident.status.in_(_ACTIVE))
    ) or 0
    return StatisticsResponse(
        total_events=int(total_events),
        threats_detected=int(threats_detected),
        active_incidents=int(active_incidents),
        critical_incidents=int(critical_incidents),
        current_risk=int(current_risk),
        note="Counts queried from SQLite. Empty until events are ingested.",
    )
