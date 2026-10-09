from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from app.config import get_settings
from app.database.session import get_engine, get_session_factory
from app.models.orm import Alert, Event, Incident, User

REQUIRED_TABLES = {
    "events",
    "incidents",
    "incident_events",
    "alerts",
    "users",
    "system_status",
}


def test_schema_creates_required_tables(client: TestClient) -> None:
    inspector = inspect(get_engine())
    assert REQUIRED_TABLES.issubset(set(inspector.get_table_names()))


def test_seeded_analyst_user(client: TestClient) -> None:
    session = get_session_factory()()
    try:
        user = session.scalar(select(User).where(User.username == "analyst"))
        assert user is not None
        assert user.role == "analyst"
        assert user.user_id == "USR-001"
    finally:
        session.close()


def test_event_round_trip(client: TestClient) -> None:
    session = get_session_factory()()
    try:
        session.add(
            Event(
                event_id="EVT-TEST-1",
                timestamp=datetime.now(timezone.utc),
                source_ip="10.0.0.41",
                destination_ip="10.0.0.10",
                user="jdoe",
                event_type="authentication",
                action="login_failed",
                status="failure",
                resource="vpn-gateway",
                protocol="https",
                source_device="laptop-sim-01",
                metadata_json={"scenario": "unit-test"},
            )
        )
        session.commit()
        stored = session.get(Event, "EVT-TEST-1")
        assert stored is not None
        assert stored.action == "login_failed"
        assert stored.metadata_json["scenario"] == "unit-test"
    finally:
        session.close()

    stats = client.get("/api/statistics").json()
    assert stats["total_events"] == 1


def test_get_events_and_filtering(client: TestClient) -> None:
    session = get_session_factory()()
    try:
        session.add_all(
            [
                Event(
                    event_id="EVT-100",
                    timestamp=datetime(2026, 10, 8, 12, 0, 0, tzinfo=timezone.utc),
                    source_ip="192.168.1.50",
                    destination_ip="192.168.1.1",
                    user="alice",
                    event_type="authentication",
                    action="login_failed",
                    metadata_json={"attempt": 1},
                ),
                Event(
                    event_id="EVT-101",
                    timestamp=datetime(2026, 10, 8, 12, 1, 0, tzinfo=timezone.utc),
                    source_ip="192.168.1.50",
                    destination_ip="192.168.1.1",
                    user="alice",
                    event_type="authentication",
                    action="login_success",
                    metadata_json={"attempt": 2},
                ),
                Event(
                    event_id="EVT-102",
                    timestamp=datetime(2026, 10, 8, 12, 5, 0, tzinfo=timezone.utc),
                    source_ip="10.10.10.20",
                    destination_ip="192.168.1.200",
                    user="bob",
                    event_type="resource_access",
                    action="access_denied",
                    resource="restricted-share",
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    # Query all events
    resp = client.get("/api/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    # Check that metadata is exposed properly in response
    assert data["items"][-1]["metadata"]["attempt"] == 1 or any(
        i["event_id"] == "EVT-100" and i["metadata"].get("attempt") == 1 for i in data["items"]
    )

    # Filter by user
    resp_user = client.get("/api/events?user=alice")
    assert resp_user.status_code == 200
    user_data = resp_user.json()
    assert user_data["total"] == 2
    assert all(i["user"] == "alice" for i in user_data["items"])

    # Filter by event_type
    resp_type = client.get("/api/events?event_type=resource_access")
    assert resp_type.status_code == 200
    type_data = resp_type.json()
    assert type_data["total"] == 1
    assert type_data["items"][0]["event_id"] == "EVT-102"

    # Get single event by ID
    resp_single = client.get("/api/events/EVT-101")
    assert resp_single.status_code == 200
    single_data = resp_single.json()
    assert single_data["event_id"] == "EVT-101"
    assert single_data["action"] == "login_success"

    # 404 for missing event
    resp_missing = client.get("/api/events/EVT-NONEXISTENT")
    assert resp_missing.status_code == 404


def test_get_alerts_from_database(client: TestClient) -> None:
    session = get_session_factory()()
    try:
        session.add_all(
            [
                Alert(
                    alert_id="ALT-001",
                    source="rule",
                    severity="HIGH",
                    title="Repeated Authentication Failures",
                    message="3 failed logins within 60s for user alice",
                    extras={"rule_id": "AUTH_BURST"},
                ),
                Alert(
                    alert_id="ALT-002",
                    source="ml",
                    severity="LOW",
                    title="Unusual Network Volume",
                    message="Anomaly score 28/100",
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    resp = client.get("/api/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # Filter by severity
    resp_high = client.get("/api/alerts?severity=HIGH")
    assert resp_high.status_code == 200
    high_data = resp_high.json()
    assert high_data["total"] == 1
    assert high_data["items"][0]["alert_id"] == "ALT-001"
    assert high_data["items"][0]["extras"]["rule_id"] == "AUTH_BURST"


def test_get_incidents_from_database(client: TestClient) -> None:
    session = get_session_factory()()
    try:
        session.add(
            Incident(
                incident_id="INC-1001",
                severity="HIGH",
                risk_score=75,
                status="NEW",
                summary="Multi-stage credential access on VPN",
                explanation="Repeated failed authentications followed by privileged access.",
                recommendation="Disable affected account and review session logs.",
                affected_user="alice",
                source_ip="192.168.1.50",
            )
        )
        session.commit()
    finally:
        session.close()

    resp = client.get("/api/incidents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["incident_id"] == "INC-1001"
    assert data["items"][0]["risk_score"] == 75

    # Get single incident
    resp_single = client.get("/api/incidents/INC-1001")
    assert resp_single.status_code == 200
    inc_data = resp_single.json()
    assert inc_data["incident_id"] == "INC-1001"
    assert inc_data["summary"] == "Multi-stage credential access on VPN"

    # Missing incident 404
    resp_missing = client.get("/api/incidents/INC-MISSING")
    assert resp_missing.status_code == 404

    # PATCH incident status update (Phase 9)
    resp_patch = client.patch("/api/incidents/INC-1001", json={"status": "INVESTIGATING"})
    assert resp_patch.status_code == 200
    assert resp_patch.json()["status"] == "INVESTIGATING"


def test_resolve_sqlite_url_under_backend() -> None:
    from app.config import BACKEND_DIR
    from app.database.session import resolve_database_url

    resolved = resolve_database_url("sqlite:///./data/logshield.db", BACKEND_DIR)
    assert resolved.startswith("sqlite:///")
    assert "data/logshield.db" in resolved.replace("\\", "/")
    get_settings()  # settings still load
