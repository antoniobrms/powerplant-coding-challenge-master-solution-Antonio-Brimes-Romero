import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

PAYLOADS = Path(__file__).resolve().parents[1] / "example_payloads"
client = TestClient(app)


def load_json(name):
    return json.loads((PAYLOADS / name).read_text())


def test_productionplan_returns_expected_response():
    response = client.post("/productionplan", json=load_json("payload3.json"))
    assert response.status_code == 200
    assert response.json() == load_json("response3.json")


def test_invalid_payload_returns_422():
    payload = load_json("payload1.json")
    del payload["fuels"]["gas(euro/MWh)"]
    assert client.post("/productionplan", json=payload).status_code == 422


def test_impossible_load_returns_422():
    payload = load_json("payload1.json")
    payload["load"] = 10000
    response = client.post("/productionplan", json=payload)
    assert response.status_code == 422
    assert "Ninguna combinación" in response.json()["detail"]
