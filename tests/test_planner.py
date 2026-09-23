import json
from pathlib import Path

import pytest

from app import main
from app.models import ProductionPlanRequest
from app.planner import NoSolutionError, Plant, plan_production

PAYLOADS = Path(__file__).resolve().parents[1] / "example_payloads"


def load_json(name):
    return json.loads((PAYLOADS / name).read_text())


def solve(payload):
    request = ProductionPlanRequest.model_validate(payload)
    return {out.name: out.p for out in main.compute_plan(request)}


def test_payload1():
    plan = solve(load_json("payload1.json"))
    assert plan == {"windpark1": 90.0, "windpark2": 21.6, "gasfiredbig1": 368.4,
                    "gasfiredbig2": 0.0, "gasfiredsomewhatsmaller": 0.0, "tj1": 0.0}


def test_payload2_needs_both_big_gas_plants():
    # Un greedy se atasca aquí: big1 a 460 deja 20 MW y big2 no baja de 100
    plan = solve(load_json("payload2.json"))
    assert plan["gasfiredbig1"] == 380.0
    assert plan["gasfiredbig2"] == 100.0
    assert sum(plan.values()) == 480


def test_payload3_matches_expected_response():
    expected = {r["name"]: r["p"] for r in load_json("response3.json")}
    assert solve(load_json("payload3.json")) == expected


def test_co2_can_change_the_merit_order(monkeypatch):
    payload = {
        "load": 100,
        "fuels": {"gas(euro/MWh)": 10, "kerosine(euro/MWh)": 12,
                  "co2(euro/ton)": 100, "wind(%)": 0},
        "powerplants": [
            {"name": "gas", "type": "gasfired", "efficiency": 0.5, "pmin": 0, "pmax": 100},
            {"name": "tj", "type": "turbojet", "efficiency": 0.5, "pmin": 0, "pmax": 100},
        ],
    }
    monkeypatch.setattr(main, "INCLUDE_CO2", False)
    assert solve(payload)["gas"] == 100.0  # gas 20 €/MWh frente a tj 24
    monkeypatch.setattr(main, "INCLUDE_CO2", True)
    assert solve(payload)["tj"] == 100.0  # con CO2 el gas sube a 20 + 0.3 * 100 = 50 €/MWh


def test_wind_is_switched_off_when_it_exceeds_the_load():
    plants = [Plant("wind", 0.0, 600, 600), Plant("gas", 25.0, 500, 1000)]
    assert plan_production(1000, plants) == {"wind": 0, "gas": 1000}


def test_load_above_capacity():
    with pytest.raises(NoSolutionError):
        plan_production(5000, [Plant("gas", 20.0, 0, 4600)])


def test_load_in_a_pmin_gap():
    # 50 MW no se pueden dar con una central que no baja de 100
    with pytest.raises(NoSolutionError):
        plan_production(500, [Plant("gas", 20.0, 1000, 4600)])
