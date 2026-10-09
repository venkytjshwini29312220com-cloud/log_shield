"""Tests for Phase 9: Incident Management, Analyst Workflow, and Timeline Reconstruction."""

from fastapi.testclient import TestClient


def test_patch_incident_status_transitions(client: TestClient) -> None:
    """Analyst progresses an incident: NEW -> INVESTIGATING -> CONTAINED -> RESOLVED."""
    ev = {
        "source_ip": "10.0.0.88",
        "user": "analyst_target",
        "event_type": "authentication",
        "action": "login_failed",
        "status": "failure",
    }
    resp = client.post("/api/events", json=ev)
    assert resp.status_code == 201

    incidents = client.get("/api/incidents").json()
    assert incidents["total"] == 1
    inc_id = incidents["items"][0]["incident_id"]
    assert incidents["items"][0]["status"] == "NEW"

    # 1. Triage: Move to INVESTIGATING
    patch1 = client.patch(
        f"/api/incidents/{inc_id}",
        json={
            "status": "INVESTIGATING",
            "notes": "Analyst investigating suspicious brute-force activity.",
            "assigned_to": "alice_analyst",
            "analyst": "alice",
        },
    )
    assert patch1.status_code == 200
    d1 = patch1.json()
    assert d1["status"] == "INVESTIGATING"
    assert d1["risk_breakdown"]["assigned_to"] == "alice_analyst"
    assert len(d1["risk_breakdown"]["notes"]) == 1
    assert len(d1["risk_breakdown"]["analyst_history"]) == 1

    # 2. Containment: Move to CONTAINED
    patch2 = client.patch(
        f"/api/incidents/{inc_id}",
        json={
            "status": "CONTAINED",
            "notes": "Host isolated; active sessions revoked.",
            "analyst": "alice",
        },
    )
    assert patch2.status_code == 200
    d2 = patch2.json()
    assert d2["status"] == "CONTAINED"
    assert len(d2["risk_breakdown"]["notes"]) == 2
    assert len(d2["risk_breakdown"]["analyst_history"]) == 2

    # 3. Resolution: Move to RESOLVED
    patch3 = client.patch(
        f"/api/incidents/{inc_id}",
        json={
            "status": "RESOLVED",
            "notes": "Remediation verified. Closing incident ticket.",
            "analyst": "alice",
        },
    )
    assert patch3.status_code == 200
    d3 = patch3.json()
    assert d3["status"] == "RESOLVED"
    assert len(d3["risk_breakdown"]["notes"]) == 3
    assert len(d3["risk_breakdown"]["analyst_history"]) == 3


def test_patch_incident_invalid_status_returns_422(client: TestClient) -> None:
    """Unsupported statuses return HTTP 422."""
    ev = {
        "source_ip": "10.0.0.15",
        "user": "test_user",
        "event_type": "authentication",
        "action": "login_failed",
    }
    client.post("/api/events", json=ev)
    inc_id = client.get("/api/incidents").json()["items"][0]["incident_id"]

    resp = client.patch(f"/api/incidents/{inc_id}", json={"status": "INVALID_STATE"})
    assert resp.status_code == 422
    assert "status" in str(resp.json()["detail"])


def test_patch_incident_not_found(client: TestClient) -> None:
    """Updating nonexistent incident returns HTTP 404."""
    resp = client.patch("/api/incidents/INC-9999", json={"status": "INVESTIGATING"})
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_add_incident_note(client: TestClient) -> None:
    """POST /api/incidents/{id}/notes appends analyst notes."""
    ev = {
        "source_ip": "10.0.0.22",
        "user": "victim1",
        "event_type": "authentication",
        "action": "login_failed",
    }
    client.post("/api/events", json=ev)
    inc_id = client.get("/api/incidents").json()["items"][0]["incident_id"]

    resp = client.post(
        f"/api/incidents/{inc_id}/notes",
        json={"note": "Firewall block rule deployed on egress switch.", "analyst": "bob"},
    )
    assert resp.status_code == 200
    data = resp.json()

    notes = data["risk_breakdown"]["notes"]
    assert len(notes) == 1
    assert notes[0]["note"] == "Firewall block rule deployed on egress switch."
    assert notes[0]["analyst"] == "bob"


def test_incident_resolution_decreases_active_incidents_in_statistics(client: TestClient) -> None:
    """Resolving or marking incident false positive updates active_incidents count in real time."""
    ev = {
        "source_ip": "10.0.0.33",
        "user": "dev1",
        "event_type": "authentication",
        "action": "login_failed",
    }
    client.post("/api/events", json=ev)
    inc_id = client.get("/api/incidents").json()["items"][0]["incident_id"]

    # When NEW, active_incidents is 1
    stats1 = client.get("/api/statistics").json()
    assert stats1["active_incidents"] == 1

    # Transition to RESOLVED -> active_incidents drops to 0
    client.patch(f"/api/incidents/{inc_id}", json={"status": "RESOLVED"})
    stats2 = client.get("/api/statistics").json()
    assert stats2["active_incidents"] == 0

    # Transition to FALSE_POSITIVE -> active_incidents remains 0
    client.patch(f"/api/incidents/{inc_id}", json={"status": "FALSE_POSITIVE"})
    stats3 = client.get("/api/statistics").json()
    assert stats3["active_incidents"] == 0


def test_incident_timeline_reconstruction(client: TestClient) -> None:
    """GET /api/incidents/{id}/timeline returns chronological items across events, alerts, and audit."""
    ev = {
        "source_ip": "10.0.0.44",
        "user": "target_user",
        "event_type": "resource_access",
        "action": "access_denied",
        "status": "denied",
        "resource": "/admin/classified",
    }
    client.post("/api/events", json=ev)
    inc_id = client.get("/api/incidents").json()["items"][0]["incident_id"]

    # Add note and change status
    client.patch(
        f"/api/incidents/{inc_id}",
        json={"status": "INVESTIGATING", "notes": "Initial investigation started"},
    )

    timeline_resp = client.get(f"/api/incidents/{inc_id}/timeline")
    assert timeline_resp.status_code == 200
    timeline = timeline_resp.json()

    assert timeline["incident_id"] == inc_id
    assert timeline["total"] >= 2
    types = {item["item_type"] for item in timeline["items"]}
    assert "event" in types
    assert "audit" in types


def test_list_incidents_filtering_by_user_and_ip(client: TestClient) -> None:
    """Incidents list supports user and source_ip query filters."""
    client.post(
        "/api/events",
        json={"source_ip": "192.168.10.5", "user": "charlie", "event_type": "authentication", "action": "login_failed"},
    )
    client.post(
        "/api/events",
        json={"source_ip": "192.168.20.9", "user": "david", "event_type": "authentication", "action": "login_failed"},
    )

    user_resp = client.get("/api/incidents?user=charlie")
    assert user_resp.status_code == 200
    assert user_resp.json()["total"] == 1
    assert user_resp.json()["items"][0]["affected_user"] == "charlie"

    ip_resp = client.get("/api/incidents?source_ip=192.168.20.9")
    assert ip_resp.status_code == 200
    assert ip_resp.json()["total"] == 1
    assert ip_resp.json()["items"][0]["source_ip"] == "192.168.20.9"
