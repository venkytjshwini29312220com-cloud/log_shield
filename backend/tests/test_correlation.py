"""Tests for Phase 7: Event Correlation Engine, Kill-Chain Reconstruction, and Incident Management."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def test_scenario_f_multi_stage_attack_correlates_to_single_incident(client: TestClient) -> None:
    """Scenario F centerpiece: Multi-stage attack (auth failures -> auth success -> resource access -> network scan)

    must correlate into EXACTLY ONE critical incident, with all 6 events ordered in timeline.
    """
    base_time = datetime(2026, 10, 9, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Three failed logins for mholmes (triggers RULE-AUTH-001)
    ev1 = {
        "timestamp": (base_time + timedelta(seconds=10)).isoformat(),
        "source_ip": "10.0.0.99",
        "user": "mholmes",
        "event_type": "authentication",
        "action": "login_failed",
        "status": "failure",
        "resource": "portal-auth",
    }
    ev2 = {
        "timestamp": (base_time + timedelta(seconds=20)).isoformat(),
        "source_ip": "10.0.0.99",
        "user": "mholmes",
        "event_type": "authentication",
        "action": "login_failed",
        "status": "failure",
        "resource": "portal-auth",
    }
    ev3 = {
        "timestamp": (base_time + timedelta(seconds=30)).isoformat(),
        "source_ip": "10.0.0.99",
        "user": "mholmes",
        "event_type": "authentication",
        "action": "login_failed",
        "status": "failure",
        "resource": "portal-auth",
    }
    # 2. Login success for mholmes (triggers RULE-AUTH-002 fail-then-success)
    ev4 = {
        "timestamp": (base_time + timedelta(seconds=45)).isoformat(),
        "source_ip": "10.0.0.99",
        "user": "mholmes",
        "event_type": "authentication",
        "action": "login_success",
        "status": "success",
        "resource": "portal-auth",
    }
    # 3. Access denied to sensitive resource (triggers RULE-ACC-001)
    ev5 = {
        "timestamp": (base_time + timedelta(seconds=60)).isoformat(),
        "source_ip": "10.0.0.99",
        "user": "mholmes",
        "event_type": "resource_access",
        "action": "access_denied",
        "status": "denied",
        "resource": "/finance/records",
    }
    # 4. Outbound port scan from the host (triggers RULE-NET-001)
    ev6 = {
        "timestamp": (base_time + timedelta(seconds=80)).isoformat(),
        "source_ip": "10.0.0.99",
        "destination_ip": "10.0.0.250",
        "user": "mholmes",
        "event_type": "network",
        "action": "port_scan",
        "status": "success",
        "resource": "subnet-scan",
    }

    resp = client.post("/api/events/batch", json={"events": [ev1, ev2, ev3, ev4, ev5, ev6]})
    assert resp.status_code == 201
    assert resp.json()["count"] == 6

    # Verify that only ONE incident was created
    incidents_resp = client.get("/api/incidents")
    assert incidents_resp.status_code == 200
    inc_data = incidents_resp.json()
    assert inc_data["total"] == 1
    assert len(inc_data["items"]) == 1

    incident = inc_data["items"][0]
    incident_id = incident["incident_id"]
    assert incident_id.startswith("INC-")
    assert incident["severity"] == "CRITICAL"
    assert incident["risk_score"] == 94
    assert incident["affected_user"] == "mholmes"
    assert incident["source_ip"] == "10.0.0.99"
    assert "Multi-stage" in incident["summary"]

    # Verify detailed incident endpoint
    detail_resp = client.get(f"/api/incidents/{incident_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()

    # Verify all 6 events are correlated in sequence
    assert len(detail["events"]) == 6
    event_ids = [e["event_id"] for e in detail["events"]]
    assert len(set(event_ids)) == 6

    # Verify associated alerts
    assert len(detail["alerts"]) >= 3
    rule_ids = {a.get("extras", {}).get("rule_id") for a in detail["alerts"] if a.get("extras")}
    assert "RULE-AUTH-001" in rule_ids
    assert "RULE-AUTH-002" in rule_ids
    assert "RULE-ACC-001" in rule_ids

    # Verify risk breakdown reflects multi-stage compromise
    bdown = detail["risk_breakdown"]
    assert bdown["multi_stage_compromise"] is True
    assert bdown["stages_count"] == 3
    assert len(bdown["correlated_stages"]) == 3

    # Verify statistics reflect the critical incident and risk 94
    stats_resp = client.get("/api/statistics")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_events"] == 6
    assert stats["active_incidents"] == 1
    assert stats["critical_incidents"] == 1
    assert stats["current_risk"] == 94


def test_correlation_join_keys(client: TestClient) -> None:
    """Test correlation joins across common IP even if username changes (e.g. pivoting/spraying)."""
    base_time = datetime(2026, 10, 9, 14, 0, 0, tzinfo=timezone.utc)

    # Event 1: user1 fails login from IP 192.168.1.100
    ev1 = {
        "timestamp": base_time.isoformat(),
        "source_ip": "192.168.1.100",
        "user": "user1",
        "event_type": "authentication",
        "action": "login_failed",
        "status": "failure",
    }
    # Event 2: user2 fails login from same IP 192.168.1.100
    ev2 = {
        "timestamp": (base_time + timedelta(seconds=30)).isoformat(),
        "source_ip": "192.168.1.100",
        "user": "user2",
        "event_type": "authentication",
        "action": "login_failed",
        "status": "failure",
    }

    client.post("/api/events", json=ev1)
    client.post("/api/events", json=ev2)

    incidents_resp = client.get("/api/incidents")
    assert incidents_resp.status_code == 200
    data = incidents_resp.json()
    # Both events from same IP should group into a single incident
    assert data["total"] == 1
    incident_id = data["items"][0]["incident_id"]

    detail = client.get(f"/api/incidents/{incident_id}").json()
    assert len(detail["events"]) == 2


def test_correlation_window_expiration(client: TestClient) -> None:
    """Events separated by more than 300 seconds window should produce distinct incidents."""
    base_time = datetime(2026, 10, 9, 10, 0, 0, tzinfo=timezone.utc)

    # First suspicious event at T=0
    ev1 = {
        "timestamp": base_time.isoformat(),
        "source_ip": "172.16.0.5",
        "user": "alice",
        "event_type": "authentication",
        "action": "login_failed",
        "status": "failure",
    }
    client.post("/api/events", json=ev1)

    # Second suspicious event at T=400s (exceeds default 300s window)
    ev2 = {
        "timestamp": (base_time + timedelta(seconds=400)).isoformat(),
        "source_ip": "172.16.0.5",
        "user": "alice",
        "event_type": "authentication",
        "action": "login_failed",
        "status": "failure",
    }
    client.post("/api/events", json=ev2)

    incidents_resp = client.get("/api/incidents")
    assert incidents_resp.status_code == 200
    data = incidents_resp.json()
    # Should have 2 distinct incidents because of window expiration
    assert data["total"] == 2


def test_benign_event_does_not_create_incident(client: TestClient) -> None:
    """A standard benign successful login without prior failures or alerts should not open an incident."""
    ev = {
        "source_ip": "10.0.0.12",
        "user": "regular_user",
        "event_type": "authentication",
        "action": "login_success",
        "status": "success",
        "resource": "dashboard",
    }
    resp = client.post("/api/events", json=ev)
    assert resp.status_code == 201

    incidents_resp = client.get("/api/incidents")
    assert incidents_resp.status_code == 200
    assert incidents_resp.json()["total"] == 0


def test_incident_filtering_by_status_and_severity(client: TestClient) -> None:
    """Incident listing supports status and severity query parameters."""
    base_time = datetime(2026, 10, 9, 8, 0, 0, tzinfo=timezone.utc)

    # Single failure -> MEDIUM incident
    client.post(
        "/api/events",
        json={
            "timestamp": base_time.isoformat(),
            "source_ip": "10.1.1.10",
            "user": "userA",
            "event_type": "authentication",
            "action": "login_failed",
            "status": "failure",
        },
    )

    # Query by severity
    med_resp = client.get("/api/incidents?severity=MEDIUM")
    assert med_resp.status_code == 200
    assert med_resp.json()["total"] == 1

    crit_resp = client.get("/api/incidents?severity=CRITICAL")
    assert crit_resp.status_code == 200
    assert crit_resp.json()["total"] == 0

    # Query by status
    new_resp = client.get("/api/incidents?status=NEW")
    assert new_resp.status_code == 200
    assert new_resp.json()["total"] == 1

    closed_resp = client.get("/api/incidents?status=RESOLVED")
    assert closed_resp.status_code == 200
    assert closed_resp.json()["total"] == 0


def test_incident_not_found(client: TestClient) -> None:
    """Requesting nonexistent incident returns 404."""
    resp = client.get("/api/incidents/INC-9999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
