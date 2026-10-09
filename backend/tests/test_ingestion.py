"""Tests for Phase 4: Event ingestion, parsing, normalization, and persistence."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient


def test_ingest_single_standard_event(client: TestClient) -> None:
    payload = {
        "source_ip": "10.0.0.41",
        "destination_ip": "10.0.0.10",
        "user": "jdoe",
        "event_type": "authentication",
        "action": "login_failed",
        "status": "failure",
        "resource": "vpn-gateway",
        "protocol": "https",
        "source_device": "laptop-sim-01",
    }
    response = client.post("/api/events", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["event_id"].startswith("EVT-")
    assert data["user"] == "jdoe"
    assert data["source_ip"] == "10.0.0.41"
    assert data["destination_ip"] == "10.0.0.10"
    assert data["event_type"] == "authentication"
    assert data["action"] == "login_failed"
    assert data["status"] == "failure"
    assert data["resource"] == "vpn-gateway"
    assert data["protocol"] == "https"
    assert data["source_device"] == "laptop-sim-01"
    assert "timestamp" in data
    assert "ingested_at" in data

    # Verify retrieval by ID
    event_id = data["event_id"]
    get_resp = client.get(f"/api/events/{event_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["event_id"] == event_id

    # Verify statistics incremented
    stats = client.get("/api/statistics").json()
    assert stats["total_events"] == 1


def test_ingest_batch_container(client: TestClient) -> None:
    payload = {
        "events": [
            {
                "user": "alice",
                "event_type": "authentication",
                "action": "login_failed",
                "source_ip": "192.168.1.50",
            },
            {
                "user": "alice",
                "event_type": "authentication",
                "action": "login_success",
                "source_ip": "192.168.1.50",
            },
        ]
    }
    response = client.post("/api/events", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["count"] == 2
    assert len(data["events"]) == 2
    assert data["events"][0]["user"] == "alice"
    assert data["events"][0]["action"] == "login_failed"
    assert data["events"][1]["action"] == "login_success"
    # Ensure sequential IDs
    assert data["events"][0]["event_id"] != data["events"][1]["event_id"]


def test_ingest_batch_array(client: TestClient) -> None:
    payload = [
        {"user": "bob", "event_type": "resource_access", "action": "access_denied", "resource": "/etc/shadow"},
        {"user": "bob", "event_type": "network", "action": "outbound_scan", "destination_ip": "10.0.0.99"},
    ]
    response = client.post("/api/events", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["count"] == 2
    assert len(data["events"]) == 2


def test_custom_event_id_and_conflict_handling(client: TestClient) -> None:
    custom_id = "EVT-CUSTOM-001"
    payload = {
        "event_id": custom_id,
        "user": "charlie",
        "event_type": "authentication",
        "action": "login_success",
    }
    resp1 = client.post("/api/events", json=payload)
    assert resp1.status_code == 201
    assert resp1.json()["event_id"] == custom_id

    # Duplicate explicit ID should return 409 Conflict
    resp2 = client.post("/api/events", json=payload)
    assert resp2.status_code == 409
    assert f"'{custom_id}' already exists" in resp2.json()["detail"]


def test_duplicate_event_id_in_same_batch(client: TestClient) -> None:
    payload = {
        "events": [
            {"event_id": "EVT-DUP-1", "user": "u1", "event_type": "auth", "action": "login"},
            {"event_id": "EVT-DUP-1", "user": "u2", "event_type": "auth", "action": "login"},
        ]
    }
    resp = client.post("/api/events", json=payload)
    assert resp.status_code == 409
    assert "Duplicate event_id" in resp.json()["detail"]


def test_field_alias_mapping(client: TestClient) -> None:
    alias_payload = {
        "src": "172.16.0.5",
        "dst": "172.16.0.100",
        "username": "dave",
        "cat": "authentication",
        "act": "login_failed",
        "res": "ssh-bastion",
        "proto": "SSH",
        "device": "bastion-host-01",
        "result": "DENIED",
    }
    resp = client.post("/api/events", json=alias_payload)
    assert resp.status_code == 201
    event = resp.json()

    assert event["source_ip"] == "172.16.0.5"
    assert event["destination_ip"] == "172.16.0.100"
    assert event["user"] == "dave"
    assert event["event_type"] == "authentication"
    assert event["action"] == "login_failed"
    assert event["resource"] == "ssh-bastion"
    assert event["protocol"] == "ssh"
    assert event["source_device"] == "bastion-host-01"
    assert event["status"] == "denied"


def test_extensible_metadata_and_secret_redaction(client: TestClient) -> None:
    payload = {
        "user": "eve",
        "event_type": "authentication",
        "action": "login_failed",
        "scenario": "brute_force_demo",
        "attempt_number": 5,
        "user_password": "PlaintextPassword123!",
        "api_key": "sec_abc123456",
        "geo_location": {"country": "US", "city": "Seattle"},
    }
    resp = client.post("/api/events", json=payload)
    assert resp.status_code == 201
    event = resp.json()

    metadata = event["metadata"]
    assert metadata["scenario"] == "brute_force_demo"
    assert metadata["attempt_number"] == 5
    assert metadata["geo_location"]["country"] == "US"
    # Secrets must be automatically redacted
    assert metadata["user_password"] == "[REDACTED]"
    assert metadata["api_key"] == "[REDACTED]"


def test_timestamp_parsing_variants(client: TestClient) -> None:
    # 1. ISO string with Z
    e1 = client.post("/api/events", json={
        "user": "t1", "event_type": "auth", "action": "login",
        "timestamp": "2026-10-08T17:30:00Z",
    }).json()
    assert "2026-10-08T17:30:00" in e1["timestamp"]

    # 2. Unix epoch timestamp
    e2 = client.post("/api/events", json={
        "user": "t2", "event_type": "auth", "action": "login",
        "timestamp": 1791480000,
    }).json()
    assert "timestamp" in e2

    # 3. Syslog date format
    e3 = client.post("/api/events", json={
        "user": "t3", "event_type": "auth", "action": "login",
        "timestamp": "Oct 08 14:15:00",
    }).json()
    assert "timestamp" in e3


def test_raw_cef_string_ingestion(client: TestClient) -> None:
    cef_log = (
        "CEF:0|LogShield|SimLab|1.0|101|login_failed|7|"
        "src=198.51.100.22 dst=10.0.0.10 suser=targetuser act=login_failed proto=https"
    )
    resp = client.post("/api/events", content=cef_log, headers={"content-type": "text/plain"})
    assert resp.status_code == 201
    event = resp.json()

    assert event["source_ip"] == "198.51.100.22"
    assert event["destination_ip"] == "10.0.0.10"
    assert event["user"] == "targetuser"
    assert event["action"] == "login_failed"
    assert event["event_type"] == "authentication"
    assert event["protocol"] == "https"
    assert event["raw"]["format"] == "cef"


def test_raw_syslog_string_ingestion(client: TestClient) -> None:
    syslog_line = (
        "Oct 8 17:00:00 laptop-sim-01 sshd[1234]: "
        "Failed password for invalid user hacker from 203.0.113.195 port 44212 ssh2"
    )
    resp = client.post("/api/events", content=syslog_line, headers={"content-type": "text/plain"})
    assert resp.status_code == 201
    event = resp.json()

    assert event["user"] == "hacker"
    assert event["source_ip"] == "203.0.113.195"
    assert event["protocol"] == "ssh2"
    assert event["event_type"] == "authentication"
    assert event["action"] == "login_failed"
    assert event["status"] == "failure"
    assert event["source_device"] == "laptop-sim-01"


def test_multi_line_text_ingestion(client: TestClient) -> None:
    lines = (
        "Oct 8 17:00:00 laptop-sim-01 sshd[1]: Failed password for invalid user hacker from 1.1.1.1 port 22 ssh2\n"
        "Oct 8 17:00:01 laptop-sim-01 sshd[2]: Accepted password for admin from 10.0.0.2 port 22 ssh2\n"
    )
    resp = client.post("/api/events", content=lines, headers={"content-type": "text/plain"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["count"] == 2
    assert data["events"][0]["user"] == "hacker"
    assert data["events"][1]["user"] == "admin"


def test_preview_parse_endpoint(client: TestClient) -> None:
    # Does not persist to SQLite
    stats_before = client.get("/api/statistics").json()["total_events"]
    raw_cef = "CEF:0|LogShield|Lab|1.0|100|login_failed|5|src=10.0.0.41 dst=10.0.0.10 suser=jdoe act=login_failed"
    resp = client.post("/api/events/parse", content=raw_cef, headers={"content-type": "text/plain"})
    assert resp.status_code == 200
    parsed = resp.json()
    assert parsed["user"] == "jdoe"
    assert parsed["source_ip"] == "10.0.0.41"

    stats_after = client.get("/api/statistics").json()["total_events"]
    assert stats_after == stats_before


def test_validation_errors(client: TestClient) -> None:
    # Empty object
    resp1 = client.post("/api/events", json={})
    assert resp1.status_code == 422

    # Empty batch
    resp2 = client.post("/api/events", json={"events": []})
    assert resp2.status_code == 422

    # Empty text
    resp3 = client.post("/api/events", content="   \n  ", headers={"content-type": "text/plain"})
    assert resp3.status_code == 422

    # Invalid JSON
    resp4 = client.post("/api/events", content="not json", headers={"content-type": "application/json"})
    assert resp4.status_code == 400


def test_query_filtering_on_ingested_events(client: TestClient) -> None:
    client.post("/api/events", json={
        "events": [
            {"user": "alice", "source_ip": "10.1.1.1", "event_type": "authentication", "action": "login_failed"},
            {"user": "bob", "source_ip": "10.1.1.2", "event_type": "network", "action": "port_scan"},
            {"user": "alice", "source_ip": "10.1.1.1", "event_type": "resource_access", "action": "read_secret"},
        ]
    })

    # Filter by user
    alice_resp = client.get("/api/events?user=alice")
    assert alice_resp.status_code == 200
    assert alice_resp.json()["total"] == 2

    # Filter by event_type
    net_resp = client.get("/api/events?event_type=network")
    assert net_resp.status_code == 200
    assert net_resp.json()["total"] == 1
    assert net_resp.json()["items"][0]["action"] == "port_scan"

    # Filter by source_ip
    ip_resp = client.get("/api/events?source_ip=10.1.1.2")
    assert ip_resp.status_code == 200
    assert ip_resp.json()["total"] == 1
