from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.detection.engine import default_rule_engine
from app.models.orm import Alert
from app.models.schemas import AlertListResponse, AlertRead

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
def list_alerts(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    source: str | None = None,
    severity: str | None = None,
    incident_id: str | None = None,
    event_id: str | None = None,
    db: Session = Depends(get_db),
) -> AlertListResponse:
    query = select(Alert)
    count_query = select(func.count()).select_from(Alert)

    if source:
        query = query.where(Alert.source == source)
        count_query = count_query.where(Alert.source == source)
    if severity:
        query = query.where(Alert.severity == severity)
        count_query = count_query.where(Alert.severity == severity)
    if incident_id:
        query = query.where(Alert.incident_id == incident_id)
        count_query = count_query.where(Alert.incident_id == incident_id)
    if event_id:
        query = query.where(Alert.event_id == event_id)
        count_query = count_query.where(Alert.event_id == event_id)

    total = db.scalar(count_query) or 0
    items = db.scalars(query.order_by(Alert.created_at.desc()).offset(offset).limit(limit)).all()

    return AlertListResponse(
        items=[AlertRead.model_validate(item) for item in items],
        total=int(total),
        limit=limit,
        offset=offset,
    )


@router.get("/rules", response_model=list[dict[str, Any]])
def list_detection_rules() -> list[dict[str, Any]]:
    """List all registered detection rules and their configurations."""
    return default_rule_engine.list_rules()


@router.get("/{alert_id}", response_model=AlertRead)
def get_alert(alert_id: str, db: Session = Depends(get_db)) -> AlertRead:
    """Retrieve an individual alert by ID."""
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found",
        )
    return AlertRead.model_validate(alert)
