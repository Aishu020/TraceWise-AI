from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_incident_list_has_sample_records():
    response = client.get("/api/incidents")
    assert response.status_code == 200
    assert any(item["id"] == "INC-2048" for item in response.json())
    assert all("signals" not in item for item in response.json())


def test_analysis_is_explainable():
    response = client.post("/api/incidents/INC-2048/analyze")
    assert response.status_code == 200
    body = response.json()
    assert body["hypotheses"]
    assert body["hypotheses"][0]["evidence"]
    assert "not calibrated probabilities" in body["disclaimer"]


def test_unknown_incident_returns_404():
    response = client.post("/api/incidents/INC-9999/analyze")
    assert response.status_code == 404
