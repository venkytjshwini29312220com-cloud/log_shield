from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "logshield-engine"
    assert body["phase"] == 10


def test_system_status_database_online(client: TestClient) -> None:
    response = client.get("/api/system-status")
    assert response.status_code == 200
    body = response.json()
    assert body["system"] == "ONLINE"
    assert body["ai_engine"] == "ONLINE"
    assert body["log_collector"] == "ONLINE"
    assert body["components"]["database"]["status"] == "ONLINE"
    assert body["components"]["log_collector"]["status"] == "ONLINE"
    assert body["components"]["ai_engine"]["status"] == "ONLINE"
    assert body["components"]["websocket"]["status"] == "ONLINE"
    assert "Isolation Forest" in body["ml_model"]
    assert body["correlation_window_seconds"] == 300
    assert body["public_base_url"].startswith("http://")
    assert body["phase"] == 10


def test_statistics_are_queried_empty(client: TestClient) -> None:
    response = client.get("/api/statistics")
    assert response.status_code == 200
    body = response.json()
    assert body["total_events"] == 0
    assert body["current_risk"] == 0
    assert body["source"] == "computed"


def test_events_empty_validation_error(client: TestClient) -> None:
    response = client.post("/api/events", json={})
    assert response.status_code == 422

