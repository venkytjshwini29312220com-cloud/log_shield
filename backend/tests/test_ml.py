"""Tests for Phase 6: Isolation Forest anomaly detection, features, and scoring."""

from fastapi.testclient import TestClient

from app.detection.features import FEATURE_NAMES, extract_features_from_event_list
from app.models.orm import Event


def test_ml_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/ml/status")
    assert response.status_code == 200
    data = response.json()
    assert data["model_name"] == "prototype Isolation Forest anomaly detector"
    assert data["status"] == "ONLINE"
    assert data["is_trained"] is True
    assert data["anomaly_threshold"] == 65
    assert len(data["feature_names"]) == 10
    assert "0-100 risk score" in data["score_scale"]


def test_ml_score_vector_and_dict(client: TestClient) -> None:
    # 1. Score normal vector
    normal_vec = [10.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.5, 0.5, 0.0, 0.0]
    resp_norm = client.post("/api/ml/score", json={"features": normal_vec})
    assert resp_norm.status_code == 200
    norm_data = resp_norm.json()
    assert 0 <= norm_data["risk_score"] <= 100
    assert norm_data["risk_score"] < 65
    assert norm_data["is_anomaly"] is False
    assert norm_data["model"] == "prototype Isolation Forest anomaly detector"

    # 2. Score anomalous vector (massive spike, 90% failures, multiple IPs, sudo execution)
    anom_vec = [100.0, 90.0, 0.9, 10.0, 8.0, 4.0, 0.9, 0.05, 0.05, 5.0]
    resp_anom = client.post("/api/ml/score", json={"features": anom_vec})
    assert resp_anom.status_code == 200
    anom_data = resp_anom.json()
    assert anom_data["risk_score"] >= 65
    assert anom_data["is_anomaly"] is True

    # 3. Score using feature dictionary
    feat_dict = {
        "event_count": 8.0,
        "failed_auth_count": 0.0,
        "fail_ratio": 0.0,
        "unique_source_ips": 1.0,
        "unique_users": 1.0,
        "unique_event_types": 2.0,
        "auth_ratio": 0.5,
        "access_ratio": 0.5,
        "network_ratio": 0.0,
        "privileged_count": 0.0,
    }
    resp_dict = client.post("/api/ml/score", json={"feature_dict": feat_dict})
    assert resp_dict.status_code == 200
    assert resp_dict.json()["is_anomaly"] is False

    # 4. Invalid vector length
    resp_inv = client.post("/api/ml/score", json={"features": [1.0, 2.0]})
    assert resp_inv.status_code == 422


def test_feature_extraction_from_events() -> None:
    events = [
        Event(event_id="E1", event_type="authentication", action="login_success", user="alice", source_ip="10.0.0.1"),
        Event(event_id="E2", event_type="authentication", action="login_failed", status="failure", user="bob", source_ip="10.0.0.2"),
        Event(event_id="E3", event_type="resource_access", action="read_file", user="alice", source_ip="10.0.0.1"),
        Event(event_id="E4", event_type="network", action="traffic", user="alice", source_ip="10.0.0.1"),
        Event(event_id="E5", event_type="privileged_command", action="sudo_cat", user="alice", source_ip="10.0.0.1"),
    ]

    features = extract_features_from_event_list(events)
    assert features["event_count"] == 5.0
    assert features["failed_auth_count"] == 1.0
    assert features["fail_ratio"] == 0.5  # 1 failure out of 2 auth
    assert features["unique_users"] == 2.0
    assert features["unique_source_ips"] == 2.0
    assert features["privileged_count"] == 1.0
    assert len(features) == len(FEATURE_NAMES)


def test_ml_anomaly_detection_on_anomalous_burst(client: TestClient) -> None:
    # Ingest a heavy burst of 25 anomalous events: high failure rates, multiple users/IPs, sudo actions
    burst = []
    for i in range(25):
        burst.append({
            "user": f"user_{i % 5}",
            "source_ip": f"192.168.1.{10 + (i % 6)}",
            "event_type": "authentication",
            "action": "login_failed",
            "status": "failure",
            "resource": "admin-portal",
        })

    # Add a privileged command to accentuate anomaly
    burst.append({
        "user": "attacker",
        "source_ip": "192.168.1.99",
        "event_type": "privileged_command",
        "action": "sudo_bash",
        "resource": "/bin/sh",
    })

    resp = client.post("/api/events", json={"events": burst})
    assert resp.status_code == 201

    # Check that an ML-sourced alert was recorded
    ml_alerts_resp = client.get("/api/alerts?source=ml")
    assert ml_alerts_resp.status_code == 200
    ml_alerts = ml_alerts_resp.json()
    assert ml_alerts["total"] >= 1
    alert = ml_alerts["items"][0]
    assert alert["source"] == "ml"
    assert "Isolation Forest" in alert["title"]
    assert alert["extras"]["risk_score"] >= 65
    assert "features" in alert["extras"]
