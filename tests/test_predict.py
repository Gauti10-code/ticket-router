"""Tests for the /predict endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    # TestClient as a context manager so the lifespan hook runs and the
    # model actually loads — without this, predictor.is_ready stays False.
    with TestClient(app) as c:
        yield c


def test_predict_returns_200(client):
    r = client.post("/predict", json={"text": "grn stuck for invoice INV1234"})
    assert r.status_code == 200


def test_predict_response_shape(client):
    body = client.post("/predict", json={"text": "grn stuck for invoice INV1234"}).json()
    assert set(body) == {"category", "priority", "confidence", "action", "alternatives"}
    assert 0.0 <= body["confidence"] <= 1.0
    assert body["action"] in {"auto_route", "human_review"}


def test_clear_ticket_is_auto_routed(client):
    body = client.post("/predict", json={"text": "unable to login invalid credentials"}).json()
    assert body["category"] == "LOGIN_ISSUE"
    assert body["action"] == "auto_route"


def test_vague_ticket_goes_to_human(client):
    body = client.post("/predict", json={"text": "something is not working please check"}).json()
    assert body["confidence"] < 0.6
    assert body["action"] == "human_review"


def test_priority_matches_category(client):
    body = client.post("/predict", json={"text": "grn stuck for invoice INV1234"}).json()
    assert body["priority"] == "P1"


def test_too_short_is_rejected(client):
    assert client.post("/predict", json={"text": "ab"}).status_code == 422


def test_missing_field_is_rejected(client):
    assert client.post("/predict", json={"ticket": "grn stuck"}).status_code == 422


def test_alternatives_are_ranked_below_top(client):
    body = client.post("/predict", json={"text": "grn stuck for invoice INV1234"}).json()
    assert all(a["confidence"] <= body["confidence"] for a in body["alternatives"])