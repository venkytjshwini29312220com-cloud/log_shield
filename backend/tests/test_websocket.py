"""Tests for Phase 10: Real-time WebSocket fan-out (/ws/events).

Validates:
  - Connection lifecycle & initial system.status handshake
  - Ping-pong keepalive protocol
  - REST status inspection (/api/websocket/status)
  - Broadcast on log ingestion (event.created)
  - Broadcast on rule/ML detection (alert.created)
  - Broadcast on correlation (incident.created, incident.updated, risk.changed)
  - Broadcast on analyst triage workflow (PATCH /api/incidents/{id}, POST notes)
  - Multi-client fan-out delivery
  - Graceful disconnect cleanup
  - Manual broadcast trigger (/api/websocket/broadcast)
"""

from fastapi.testclient import TestClient


def test_websocket_connect_and_welcome(client: TestClient) -> None:
    with client.websocket_connect("/ws/events") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "system.status"
        assert "timestamp" in msg
        payload = msg["payload"]
        assert payload["system"] == "ONLINE"
        assert payload["websocket"] == "ONLINE"
        assert payload["active_connections"] == 1
        assert payload["phase"] == 10


def test_websocket_ping_pong_text_and_json(client: TestClient) -> None:
    with client.websocket_connect("/ws/events") as ws:
        # Initial welcome packet
        welcome = ws.receive_json()
        assert welcome["type"] == "system.status"

        # 1. Plain text ping
        ws.send_text("ping")
        resp1 = ws.receive_json()
        assert resp1["type"] == "pong"
        assert resp1["payload"]["status"] == "ok"

        # 2. JSON ping
        ws.send_json({"type": "ping"})
        resp2 = ws.receive_json()
        assert resp2["type"] == "pong"
        assert resp2["payload"]["status"] == "ok"


def test_websocket_status_rest_endpoint(client: TestClient) -> None:
    # Before connection
    res1 = client.get("/api/websocket/status")
    assert res1.status_code == 200
    b1 = res1.json()
    assert b1["status"] == "ONLINE"
    assert b1["endpoint"] == "/ws/events"
    assert "event.created" in b1["supported_events"]
    assert "incident.created" in b1["supported_events"]
    assert "risk.changed" in b1["supported_events"]

    # While connected
    with client.websocket_connect("/ws/events") as ws:
        _ = ws.receive_json()  # welcome
        res2 = client.get("/api/websocket/status")
        assert res2.status_code == 200
        assert res2.json()["active_connections"] == 1

    # After disconnect
    res3 = client.get("/api/websocket/status")
    assert res3.status_code == 200
    assert res3.json()["active_connections"] == 0


def test_websocket_broadcast_benign_event(client: TestClient) -> None:
    with client.websocket_connect("/ws/events") as ws:
        _ = ws.receive_json()  # welcome

        # Ingest a benign event
        event_payload = {
            "timestamp": "2026-10-09T04:00:00Z",
            "source_ip": "10.0.0.50",
            "user": "alice",
            "event_type": "authentication",
            "action": "login_success",
            "status": "success",
            "resource": "portal",
        }
        res = client.post("/api/events", json=event_payload)
        assert res.status_code == 201
        created_evt = res.json()

        # Receive broadcast
        msg = ws.receive_json()
        assert msg["type"] == "event.created"
        assert msg["payload"]["event_id"] == created_evt["event_id"]
        assert msg["payload"]["user"] == "alice"
        assert msg["payload"]["action"] == "login_success"


def test_websocket_broadcast_suspicious_event_alerts_and_incident(client: TestClient) -> None:
    with client.websocket_connect("/ws/events") as ws:
        _ = ws.receive_json()  # welcome

        # Ingest repeated failed logins (will trigger repeated_failed_auth rule and open incident)
        for i in range(4):
            client.post(
                "/api/events",
                json={
                    "timestamp": f"2026-10-09T04:10:0{i}Z",
                    "source_ip": "10.0.0.99",
                    "user": "attacker_ws",
                    "event_type": "authentication",
                    "action": "login_failed",
                    "status": "failure",
                    "resource": "ssh-server",
                },
            )
            # Drain messages emitted for each event
            # Event 0-2: event.created + incident.created/updated
            # Event 3: event.created + alert.created + incident.updated + risk.changed
            # We can collect all incoming messages into a list
        
        messages = []
        # Receive queued messages
        while True:
            try:
                # With TestClient, we can check if messages are available
                # or receive known count
                m = ws.receive_json()
                messages.append(m)
                if len(messages) >= 8:
                    break
            except Exception:
                break

        msg_types = [m["type"] for m in messages]
        assert "event.created" in msg_types
        assert "incident.created" in msg_types
        assert "risk.changed" in msg_types


def test_websocket_broadcast_on_incident_patch_and_note(client: TestClient) -> None:
    # 1. Create an incident first
    res = client.post(
        "/api/events",
        json={
            "timestamp": "2026-10-09T05:00:00Z",
            "source_ip": "10.0.0.123",
            "user": "victim1",
            "event_type": "resource_access",
            "action": "access_denied",
            "status": "denied",
            "resource": "/etc/shadow",
        },
    )
    assert res.status_code == 201

    incidents_res = client.get("/api/incidents")
    assert incidents_res.status_code == 200
    inc_list = incidents_res.json()["items"]
    assert len(inc_list) > 0
    inc_id = inc_list[0]["incident_id"]

    # 2. Connect WebSocket client
    with client.websocket_connect("/ws/events") as ws:
        _ = ws.receive_json()  # welcome

        # 3. Analyst patches incident status to INVESTIGATING
        patch_res = client.patch(
            f"/api/incidents/{inc_id}",
            json={
                "status": "INVESTIGATING",
                "notes": "Analyst triaging access denial.",
                "assigned_to": "analyst_bob",
            },
        )
        assert patch_res.status_code == 200

        # Receive broadcast
        msg = ws.receive_json()
        assert msg["type"] == "incident.updated"
        assert msg["payload"]["incident_id"] == inc_id
        assert msg["payload"]["status"] == "INVESTIGATING"

        # 4. Analyst appends note
        note_res = client.post(
            f"/api/incidents/{inc_id}/notes",
            json={"note": "Confirmed user account is locked.", "analyst": "analyst_bob"},
        )
        assert note_res.status_code == 200

        # Receive note broadcast
        msg2 = ws.receive_json()
        assert msg2["type"] == "incident.updated"
        assert msg2["payload"]["incident_id"] == inc_id


def test_websocket_multiple_clients_fan_out(client: TestClient) -> None:
    with client.websocket_connect("/ws/events") as ws1:
        _ = ws1.receive_json()  # welcome ws1
        with client.websocket_connect("/ws/events") as ws2:
            _ = ws2.receive_json()  # welcome ws2

            # Post event
            res = client.post(
                "/api/events",
                json={
                    "timestamp": "2026-10-09T06:00:00Z",
                    "source_ip": "10.0.0.77",
                    "user": "multi_user",
                    "event_type": "network",
                    "action": "dns_query",
                    "status": "success",
                    "resource": "internal-dns",
                },
            )
            assert res.status_code == 201

            m1 = ws1.receive_json()
            m2 = ws2.receive_json()

            assert m1["type"] == "event.created"
            assert m2["type"] == "event.created"
            assert m1["payload"]["user"] == "multi_user"
            assert m2["payload"]["user"] == "multi_user"


def test_websocket_manual_broadcast_endpoint(client: TestClient) -> None:
    with client.websocket_connect("/ws/events") as ws:
        _ = ws.receive_json()  # welcome

        # Call POST /api/websocket/broadcast
        broadcast_res = client.post(
            "/api/websocket/broadcast",
            json={
                "type": "system.status",
                "payload": {"message": "routine-check", "status": "ONLINE"},
            },
        )
        assert broadcast_res.status_code == 200
        assert broadcast_res.json()["recipients"] == 1

        msg = ws.receive_json()
        assert msg["type"] == "system.status"
        assert msg["payload"]["message"] == "routine-check"
