import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_returns_200(client):
    assert client.get("/health").status_code == 200


def test_health_payload(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert set(body) == {"status", "app", "version", "environment"}


def test_ready_reports_no_model_yet(client):
    body = client.get("/ready").json()
    assert body["model_loaded"] is False


def test_unknown_route_404s(client):
    assert client.get("/nope").status_code == 404

def test_ready_reports_model_state(client):
    body = client.get("/ready").json()
    assert isinstance(body["model_loaded"], bool)    