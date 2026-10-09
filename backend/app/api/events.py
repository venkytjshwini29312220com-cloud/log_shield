import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.orm import Event
from app.models.schemas import EventBatchResponse, EventListResponse, EventRead
from app.services.ingestion import IngestionService
from app.services.parser import LogParser

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post(
    "",
    response_model=EventRead | EventBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest log event or batch",
    description=(
        "Ingest a single event or a batch of events. Normalizes fields against the canonical "
        "event schema, extracts unknown keys to metadata, redacts sensitive credentials, "
        "assigns unique event_id if omitted, and persists to SQLite."
    ),
)
async def create_events(
    request: Request,
    db: Session = Depends(get_db),
) -> EventRead | EventBatchResponse:
    content_type = request.headers.get("content-type", "")

    if "text/" in content_type:
        raw_body = (await request.body()).decode("utf-8")
        result = IngestionService.ingest_text(db, raw_body)
        await asyncio.sleep(0)
        return result

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON request body: {exc}",
        ) from exc

    if isinstance(body, dict):
        if "events" in body and isinstance(body["events"], list):
            result = IngestionService.ingest_batch(db, body["events"])
        else:
            result = IngestionService.ingest_single(db, body)
    elif isinstance(body, list):
        result = IngestionService.ingest_batch(db, body)
    elif isinstance(body, str):
        result = IngestionService.ingest_text(db, body)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unexpected body structure. Expected JSON object or array of events.",
        )

    await asyncio.sleep(0)
    return result


@router.post(
    "/batch",
    response_model=EventBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest batch of log events",
)
async def create_events_batch(
    request: Request,
    db: Session = Depends(get_db),
) -> EventBatchResponse:
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON request body: {exc}",
        ) from exc

    if isinstance(body, dict) and "events" in body and isinstance(body["events"], list):
        result = IngestionService.ingest_batch(db, body["events"])
    elif isinstance(body, list):
        result = IngestionService.ingest_batch(db, body)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Expected JSON object with 'events' array or a JSON array of events.",
        )

    await asyncio.sleep(0)
    return result


@router.post(
    "/parse",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Preview log parsing and normalization",
    description="Normalize a raw event or log line without storing it to the database.",
)
async def preview_parse(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "text/" in content_type:
        raw_body = (await request.body()).decode("utf-8")
        return LogParser.parse(raw_body.strip())

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON request body: {exc}",
        ) from exc
    return LogParser.parse(body)


@router.get("", response_model=EventListResponse)
def list_events(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: str | None = None,
    source_ip: str | None = None,
    event_type: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    db: Session = Depends(get_db),
) -> EventListResponse:
    query = select(Event)
    count_query = select(func.count()).select_from(Event)

    if user:
        query = query.where(Event.user == user)
        count_query = count_query.where(Event.user == user)
    if source_ip:
        query = query.where(Event.source_ip == source_ip)
        count_query = count_query.where(Event.source_ip == source_ip)
    if event_type:
        query = query.where(Event.event_type == event_type)
        count_query = count_query.where(Event.event_type == event_type)
    if since:
        query = query.where(Event.timestamp >= since)
        count_query = count_query.where(Event.timestamp >= since)
    if until:
        query = query.where(Event.timestamp <= until)
        count_query = count_query.where(Event.timestamp <= until)

    total = db.scalar(count_query) or 0
    items = db.scalars(query.order_by(Event.timestamp.desc()).offset(offset).limit(limit)).all()

    return EventListResponse(
        items=[EventRead.model_validate(item) for item in items],
        total=int(total),
        limit=limit,
        offset=offset,
    )


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: str, db: Session = Depends(get_db)) -> EventRead:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{event_id}' not found",
        )
    return EventRead.model_validate(event)
