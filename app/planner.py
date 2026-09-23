from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Plant:
    name: str
    cost: float  # €/MWh
    pmin: int  # en décimas de MW
    pmax: int  # en décimas de MW


class NoSolutionError(Exception):
    pass


def dispatch(load: int, plants_on: List[Plant]) -> List[int]:
    # Todas arrancan en su pmin y lo que falta se reparte de la más barata a la más cara
    production = [p.pmin for p in plants_on]
    missing = load - sum(production)
    for i, plant in enumerate(plants_on):
        extra = min(plant.pmax - plant.pmin, missing)
        production[i] += extra
        missing -= extra
    return production


def plan_production(load: int, plants: List[Plant]) -> Dict[str, int]:
    # Recorre las centrales por orden de mérito decidiendo encender/apagar cada una,
    # y descarta las ramas que ya no pueden cuadrar con la carga
    plants = sorted(plants, key=lambda p: (p.cost, p.name))
    n = len(plants)

    # max_from[i]: lo máximo que pueden dar juntas las centrales de i en adelante
    max_from = [0] * (n + 1)
    for i in range(n - 1, -1, -1):
        max_from[i] = max_from[i + 1] + plants[i].pmax

    best = {"cost": None, "on": [], "production": []}
    on: List[Plant] = []

    def search(i: int, sum_pmin: int, sum_pmax: int) -> None:
        # Con lo encendido ya me paso aunque todas vayan al mínimo
        if sum_pmin > load:
            return
        # Aunque encienda todo lo que queda no llego
        if sum_pmax + max_from[i] < load:
            return

        if i == n:
            production = dispatch(load, on)
            cost = sum(p.cost * mw for p, mw in zip(on, production)) / 10
            if best["cost"] is None or cost < best["cost"] - 1e-6:
                best.update(cost=cost, on=list(on), production=production)
            elif abs(cost - best["cost"]) <= 1e-6 and len(on) < len(best["on"]):
                # Mismo coste: me quedo con el plan que enciende menos centrales
                best.update(cost=cost, on=list(on), production=production)
            return

        plant = plants[i]
        on.append(plant)
        search(i + 1, sum_pmin + plant.pmin, sum_pmax + plant.pmax)
        on.pop()
        search(i + 1, sum_pmin, sum_pmax)

    search(0, 0, 0)

    if best["cost"] is None:
        raise NoSolutionError(f"Ninguna combinación de centrales puede producir exactamente {load / 10} MW")

    result = {p.name: 0 for p in plants}
    for plant, mw in zip(best["on"], best["production"]):
        result[plant.name] = mw
    return result
