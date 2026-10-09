"""API response and domain models for LogShield."""

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ComponentStatus = Literal["ONLINE", "NOT_READY", "OFFLINE"]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["logshield-engine"]
    phase: int


class ComponentHealth(BaseModel):
    status: ComponentStatus
    detail: str


class SystemStatusResponse(BaseModel):
    system: ComponentStatus
    ai_engine: ComponentStatus
    log_collector: ComponentStatus
    ml_model: str
    correlation_window_seconds: int
    public_base_url: str
    phase: int
    components: dict[str, ComponentHealth]


class StatisticsResponse(BaseModel):
    total_events: int = 0
    threats_detected: int = 0
    active_incidents: int = 0
    critical_incidents: int = 0
    current_risk: int = Field(default=0, ge=0, le=100)
    source: Literal["computed"] = "computed"
    note: str | None = None


# --- Phase 3 Persistence and Normalized Models ---


class EventBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    timestamp: datetime
    source_ip: str | None = None
    destination_ip: str | None = None
    user: str | None = None
    event_type: str
    action: str
    status: str | None = None
    resource: str | None = None
    protocol: str | None = None
    source_device: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_json")
    raw: dict[str, Any] | None = None


class EventCreate(BaseModel):
    """Schema for incoming log events during ingestion (Phase 4)."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    event_id: str | None = None
    timestamp: datetime | str | None = None
    source_ip: str | None = None
    destination_ip: str | None = None
    user: str | None = None
    event_type: str | None = None
    action: str | None = None
    status: str | None = None
    resource: str | None = None
    protocol: str | None = None
    source_device: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] | str | None = None


class EventBatchCreate(BaseModel):
    """Container for batch event ingestion."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    events: list[EventCreate | dict[str, Any] | str]


class EventBatchResponse(BaseModel):
    """Response returned upon ingesting multiple events."""

    events: list["EventRead"]
    count: int


class EventRead(EventBase):
    event_id: str
    ingested_at: datetime


class EventListResponse(BaseModel):
    items: list[EventRead]
    total: int
    limit: int
    offset: int


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alert_id: str
    created_at: datetime
    source: str
    severity: str
    title: str
    message: str
    event_id: str | None = None
    incident_id: str | None = None
    extras: dict[str, Any] = Field(default_factory=dict)


class AlertListResponse(BaseModel):
    items: list[AlertRead]
    total: int
    limit: int
    offset: int


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    incident_id: str
    created_at: datetime
    updated_at: datetime
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    severity: str
    risk_score: int = 0
    status: str = "NEW"
    summary: str = ""
    explanation: str = ""
    recommendation: str = ""
    affected_user: str | None = None
    source_ip: str | None = None
    resource: str | None = None
    risk_breakdown: dict[str, Any] = Field(default_factory=dict)


class IncidentDetail(IncidentRead):
    """Detailed incident response including timeline events and detection alerts."""

    events: list[EventRead] = Field(default_factory=list)
    alerts: list[AlertRead] = Field(default_factory=list)


class IncidentListResponse(BaseModel):
    items: list[IncidentRead]
    total: int
    limit: int
    offset: int


# --- Phase 9 Incident Management Schemas ---

IncidentStatusType = Literal["NEW", "INVESTIGATING", "CONTAINED", "RESOLVED", "FALSE_POSITIVE"]


class IncidentUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: IncidentStatusType | None = None
    notes: str | None = None
    assigned_to: str | None = None
    analyst: str | None = "analyst"


class IncidentNoteCreate(BaseModel):
    note: str
    analyst: str | None = "analyst"


class TimelineItem(BaseModel):
    timestamp: datetime
    item_type: str  # event | alert | audit
    title: str
    details: dict[str, Any] = Field(default_factory=dict)


class IncidentTimelineResponse(BaseModel):
    incident_id: str
    items: list[TimelineItem]
    total: int


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: str
    display_name: str
    role: str
    created_at: datetime


# --- Phase 8 Risk Engine Models ---


class RiskWeightsResponse(BaseModel):
    weights: dict[str, float]
    severity_bands: dict[str, str]
    formula: str


class RiskCalculateRequest(BaseModel):
    rule_score: float = Field(ge=0.0, le=100.0, description="Rule-based detection score 0–100")
    ml_score: float = Field(ge=0.0, le=100.0, description="Machine learning anomaly score 0–100")
    correlation_score: float = Field(ge=0.0, le=100.0, description="Kill-chain correlation score 0–100")
    behavioral_score: float = Field(ge=0.0, le=100.0, description="Asset & behavioral context score 0–100")
    custom_weights: dict[str, float] | None = None


class RiskCalculateResponse(BaseModel):
    composite_score: int
    severity: str
    weights: dict[str, float]
    components: dict[str, int]
    contributions: dict[str, float]
    display_label: str


# --- Phase 10 WebSocket Fan-out Schemas ---

WebSocketEventType = Literal[
    "event.created",
    "alert.created",
    "incident.created",
    "incident.updated",
    "risk.changed",
    "system.status",
    "pong",
]


class WebSocketMessage(BaseModel):
    type: WebSocketEventType | str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)


class WebSocketStatusResponse(BaseModel):
    status: Literal["ONLINE", "OFFLINE"]
    active_connections: int
    endpoint: str
    supported_events: list[str]


class WebSocketBroadcastRequest(BaseModel):
    type: str = Field(default="system.status")
    payload: dict[str, Any] = Field(default_factory=dict)

