"""Tests for Phase 5: Security Rule Engine, detection rules, and alert generation."""

from fastapi.testclient import TestClient


def test_list_detection_rules(client: TestClient) -> None:
    response = client.get("/api/alerts/rules")
    assert response.status_code == 200
    rules = response.json()
    assert len(rules) >= 6
    rule_ids = {r["rule_id"] for r in rules}
    assert "RULE-AUTH-001" in rule_ids
    assert "RULE-AUTH-002" in rule_ids
    assert "RULE-AUTH-003" in rule_ids
    assert "RULE-ACC-001" in rule_ids
    assert "RULE-PRV-001" in rule_ids
    assert "RULE-NET-001" in rule_ids
    assert all(r["status"] == "ENABLED" for r in rules)


def test_repeated_failed_auth_rule(client: TestClient) -> None:
    # 1. First 2 failures do not trigger an alert (threshold is 3)
    for i in range(2):
        res = client.post("/api/events", json={
            "user": "victim_user",
            "source_ip": "10.0.0.99",
            "event_type": "authentication",
            "action": "login_failed",
            "status": "failure",
        })
        assert res.status_code == 201

    alerts_resp1 = client.get("/api/alerts?source=rule")
    assert alerts_resp1.json()["total"] == 0

    # 2. 3rd failure reaches threshold -> triggers alert
    client.post("/api/events", json={
        "user": "victim_user",
        "source_ip": "10.0.0.99",
        "event_type": "authentication",
        "action": "login_failed",
        "status": "failure",
    })

    alerts_resp2 = client.get("/api/alerts?source=rule")
    assert alerts_resp2.status_code == 200
    data = alerts_resp2.json()
    assert data["total"] == 1
    alert = data["items"][0]
    assert alert["alert_id"].startswith("ALT-")
    assert alert["source"] == "rule"
    assert alert["severity"] == "MEDIUM"
    assert "Repeated Authentication Failures" in alert["title"]
    assert alert["extras"]["failure_count"] == 3
    assert alert["extras"]["user"] == "victim_user"

    # Statistics should reflect threat count
    stats = client.get("/api/statistics").json()
    assert stats["threats_detected"] >= 1
    assert stats["total_events"] == 3


def test_fail_then_success_auth_rule(client: TestClient) -> None:
    # Send 2 failed logins
    for _ in range(2):
        client.post("/api/events", json={
            "user": "target_user",
            "event_type": "authentication",
            "action": "login_failed",
            "source_ip": "192.168.1.100",
        })

    # Send 1 successful login
    resp = client.post("/api/events", json={
        "user": "target_user",
        "event_type": "authentication",
        "action": "login_success",
        "source_ip": "192.168.1.100",
    })
    assert resp.status_code == 201
    evt_id = resp.json()["event_id"]

    # Check alert was generated for the successful login event
    alerts = client.get(f"/api/alerts?source=rule&event_id={evt_id}").json()
    assert alerts["total"] == 1
    alert = alerts["items"][0]
    assert alert["severity"] == "HIGH"
    assert "Successful Login After Multiple Failures" in alert["title"]
    assert alert["extras"]["user"] == "target_user"


def test_password_spraying_rule(client: TestClient) -> None:
    attacker_ip = "198.51.100.5"
    users = ["user_alpha", "user_beta", "user_gamma"]

    for u in users:
        client.post("/api/events", json={
            "user": u,
            "source_ip": attacker_ip,
            "event_type": "authentication",
            "action": "login_failed",
        })

    alerts = client.get("/api/alerts?severity=HIGH").json()
    spraying_alerts = [a for a in alerts["items"] if "Spraying" in a["title"]]
    assert len(spraying_alerts) >= 1
    alert = spraying_alerts[0]
    assert alert["extras"]["source_ip"] == attacker_ip
    assert alert["extras"]["distinct_accounts"] >= 3


def test_unauthorized_resource_access_rule(client: TestClient) -> None:
    # Denied access to sensitive resource
    resp = client.post("/api/events", json={
        "user": "guest_user",
        "source_ip": "10.0.0.50",
        "event_type": "resource_access",
        "action": "access_denied",
        "resource": "/etc/shadow",
        "status": "denied",
    })
    evt_id = resp.json()["event_id"]

    alerts = client.get(f"/api/alerts?event_id={evt_id}").json()
    assert alerts["total"] == 1
    alert = alerts["items"][0]
    assert alert["severity"] == "HIGH"
    assert "Unauthorized Access Attempt" in alert["title"]
    assert alert["extras"]["is_sensitive_target"] is True


def test_privileged_command_rule(client: TestClient) -> None:
    resp = client.post("/api/events", json={
        "user": "dev_user",
        "event_type": "privileged_command",
        "action": "sudo_execution",
        "resource": "rm -rf /var/log",
    })
    evt_id = resp.json()["event_id"]

    alerts = client.get(f"/api/alerts?event_id={evt_id}").json()
    assert alerts["total"] == 1
    alert = alerts["items"][0]
    assert alert["severity"] == "HIGH"
    assert "Privileged Command Execution" in alert["title"]


def test_abnormal_network_activity_rule(client: TestClient) -> None:
    resp = client.post("/api/events", json={
        "source_ip": "10.10.10.5",
        "destination_ip": "192.168.1.1",
        "event_type": "network",
        "action": "port_scan",
        "protocol": "tcp",
    })
    evt_id = resp.json()["event_id"]

    alerts = client.get(f"/api/alerts?source=rule&event_id={evt_id}").json()
    assert alerts["total"] == 1
    alert = alerts["items"][0]
    assert alert["severity"] == "HIGH"
    assert "Port Scan" in alert["title"]


def test_get_alert_by_id_and_404(client: TestClient) -> None:
    # Trigger an alert
    client.post("/api/events", json={
        "user": "admin",
        "event_type": "privileged_command",
        "action": "sudo_execution",
        "resource": "systemctl restart firewall",
    })

    alerts = client.get("/api/alerts").json()
    assert alerts["total"] >= 1
    alert_id = alerts["items"][0]["alert_id"]

    # 1. Fetch valid alert
    resp = client.get(f"/api/alerts/{alert_id}")
    assert resp.status_code == 200
    assert resp.json()["alert_id"] == alert_id

    # 2. 404 on missing alert
    missing_resp = client.get("/api/alerts/ALT-NONEXISTENT")
    assert missing_resp.status_code == 404
