"""Windowed feature extraction for Isolation Forest anomaly detection (Phase 6).

Extracts 10 behavioral numerical features over a sliding time window in SQLite:
  1. event_count
  2. failed_auth_count
  3. fail_ratio
  4. unique_source_ips
  5. unique_users
  6. unique_event_types
  7. auth_ratio
  8. access_ratio
  9. network_ratio
  10. privileged_count
"""

from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.orm import Event

FEATURE_NAMES = [
    "event_count",
    "failed_auth_count",
    "fail_ratio",
    "unique_source_ips",
    "unique_users",
    "unique_event_types",
    "auth_ratio",
    "access_ratio",
    "network_ratio",
    "privileged_count",
]


def extract_features_from_event_list(events: list[Event]) -> dict[str, float]:
    """Compute 10-dimensional feature dictionary from a list of events in window."""
    total = len(events)
    if total == 0:
        return {f: 0.0 for f in FEATURE_NAMES}

    failed_auth = 0
    total_auth = 0
    access_count = 0
    network_count = 0
    privileged_count = 0

    ips = set()
    users = set()
    types = set()

    for e in events:
        etype = (e.event_type or "").lower()
        act = (e.action or "").lower()
        stat = (e.status or "").lower()

        if e.source_ip:
            ips.add(e.source_ip)
        if e.user:
            users.add(e.user)
        if e.event_type:
            types.add(e.event_type)

        if etype == "authentication":
            total_auth += 1
            if act == "login_failed" or stat in ("failure", "failed", "denied"):
                failed_auth += 1
        elif etype in ("resource_access", "access"):
            access_count += 1
        elif etype == "network":
            network_count += 1
        elif etype in ("privileged_command", "privilege_escalation") or "sudo" in act:
            privileged_count += 1

    fail_ratio = (failed_auth / max(1, total_auth)) if total_auth > 0 else 0.0
    auth_ratio = total_auth / total
    access_ratio = access_count / total
    network_ratio = network_count / total

    return {
        "event_count": float(total),
        "failed_auth_count": float(failed_auth),
        "fail_ratio": round(fail_ratio, 4),
        "unique_source_ips": float(len(ips)),
        "unique_users": float(len(users)),
        "unique_event_types": float(len(types)),
        "auth_ratio": round(auth_ratio, 4),
        "access_ratio": round(access_ratio, 4),
        "network_ratio": round(network_ratio, 4),
        "privileged_count": float(privileged_count),
    }


def extract_features_from_db(
    session: Session,
    event: Event,
    window_seconds: int = 300,
) -> dict[str, float]:
    """Query sliding window from SQLite and extract 10-dimensional feature dictionary."""
    window_start = event.timestamp - timedelta(seconds=window_seconds)

    # Fetch all events in this window up to and including the current event
    stmt = (
        select(Event)
        .where(
            Event.timestamp >= window_start,
            Event.timestamp <= event.timestamp,
        )
        .order_by(Event.timestamp.asc())
    )
    events = list(session.scalars(stmt).all())
    if not events:
        events = [event]

    return extract_features_from_event_list(events)


def vector_from_dict(feat_dict: dict[str, float]) -> list[float]:
    """Convert feature dictionary to ordered feature vector."""
    return [feat_dict.get(name, 0.0) for name in FEATURE_NAMES]
