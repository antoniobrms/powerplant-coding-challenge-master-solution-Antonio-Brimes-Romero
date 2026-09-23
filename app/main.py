import logging
import os
from typing import List

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.models import Fuels, PowerPlant, PowerPlantOutput, ProductionPlanRequest
from app.planner import NoSolutionError, Plant, plan_production

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("powerplant")

INCLUDE_CO2 = os.getenv("INCLUDE_CO2", "true").lower() == "true"
CO2_TON_PER_MWH = 0.3

app = FastAPI(title="Plan de producción de centrales")


def to_tenths(value: float) -> int:
    return round(value * 10)


def cost_per_mwh(plant: PowerPlant, fuels: Fuels) -> float:
    if plant.type == "gasfired":
        cost = fuels.gas / plant.efficiency
        if INCLUDE_CO2:
            cost += CO2_TON_PER_MWH * fuels.co2
        return cost
    if plant.type == "turbojet":
        return fuels.kerosine / plant.efficiency
    return 0.0  # eólica


def to_plant(plant: PowerPlant, fuels: Fuels) -> Plant:
    if plant.type == "windturbine":
        # La eólica va entera (lo que dé el viento) o apagada
        output = to_tenths(plant.pmax * fuels.wind / 100)
        return Plant(plant.name, 0.0, output, output)
    return Plant(plant.name, cost_per_mwh(plant, fuels), to_tenths(plant.pmin), to_tenths(plant.pmax))


def compute_plan(request: ProductionPlanRequest) -> List[PowerPlantOutput]:
    plants = [to_plant(p, request.fuels) for p in request.powerplants]
    production = plan_production(to_tenths(request.load), plants)
    ordered = sorted(plants, key=lambda p: (p.cost, p.name))
    return [PowerPlantOutput(name=p.name, p=production[p.name] / 10) for p in ordered]


@app.post("/productionplan", response_model=List[PowerPlantOutput])
def production_plan(request: ProductionPlanRequest):
    logger.info("Petición: carga=%s MW, %d centrales", request.load, len(request.powerplants))
    return compute_plan(request)


@app.exception_handler(NoSolutionError)
async def no_solution_handler(request: Request, exc: NoSolutionError):
    logger.warning("Sin solución: %s", exc)
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    logger.exception("Error inesperado")
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888)
