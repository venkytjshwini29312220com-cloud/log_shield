"""SQLite ORM tables for the LogShield prototype."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Event(Base):
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_ip: Mapped[str | None] = mapped_column(String(64), index=True)
    destination_ip: Mapped[str | None] = mapped_column(String(64), index=True)
    user: Mapped[str | None] = mapped_column("user", String(256), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str | None] = mapped_column(String(64))
    resource: Mapped[str | None] = mapped_column(String(512), index=True)
    protocol: Mapped[str | None] = mapped_column(String(64))
    source_device: Mapped[str | None] = mapped_column(String(256))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    incident_links: Mapped[list["IncidentEvent"]] = relationship(back_populates="event")


class Incident(Base):
    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    severity: Mapped[str] = mapped_column(String(16), index=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="NEW", index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    explanation: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(Text, default="")
    affected_user: Mapped[str | None] = mapped_column(String(256), index=True)
    source_ip: Mapped[str | None] = mapped_column(String(64), index=True)
    resource: Mapped[str | None] = mapped_column(String(512))
    risk_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    event_links: Mapped[list["IncidentEvent"]] = relationship(back_populates="incident")


class IncidentEvent(Base):
    __tablename__ = "incident_events"
    __table_args__ = (UniqueConstraint("incident_id", "event_id", name="uq_incident_event"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.incident_id", ondelete="CASCADE"), index=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.event_id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)

    incident: Mapped[Incident] = relationship(back_populates="event_links")
    event: Mapped[Event] = relationship(back_populates="incident_links")


class Alert(Base):
    __tablename__ = "alerts"

    alert_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    source: Mapped[str] = mapped_column(String(32))  # rule | ml | correlation
    severity: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(512))
    message: Mapped[str] = mapped_column(Text, default="")
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.event_id", ondelete="SET NULL"), nullable=True)
    incident_id: Mapped[str | None] = mapped_column(
        ForeignKey("incidents.incident_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    extras: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(64), default="analyst")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SystemStatus(Base):
    __tablename__ = "system_status"

    component: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32))
    detail: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# Imported so metadata includes these tables even if only Base is used.
__all__ = [
    "Alert",
    "Event",
    "Incident",
    "IncidentEvent",
    "SystemStatus",
    "User",
]
