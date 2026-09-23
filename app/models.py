from typing import List, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Fuels(BaseModel):
    gas: float = Field(alias="gas(euro/MWh)", ge=0)
    kerosine: float = Field(alias="kerosine(euro/MWh)", ge=0)
    co2: float = Field(alias="co2(euro/ton)", ge=0)
    wind: float = Field(alias="wind(%)", ge=0, le=100)


class PowerPlant(BaseModel):
    name: str
    type: Literal["gasfired", "turbojet", "windturbine"]
    efficiency: float = Field(gt=0)
    pmin: float = Field(ge=0)
    pmax: float = Field(ge=0)

    @model_validator(mode="after")
    def check_pmin_pmax(self):
        if self.pmin > self.pmax:
            raise ValueError("pmin no puede ser mayor que pmax")
        return self


class ProductionPlanRequest(BaseModel):
    load: float = Field(ge=0)
    fuels: Fuels
    powerplants: List[PowerPlant]

    @field_validator("powerplants")
    @classmethod
    def check_unique_names(cls, plants):
        names = [p.name for p in plants]
        if len(names) != len(set(names)):
            raise ValueError("los nombres de las centrales deben ser únicos")
        return plants


class PowerPlantOutput(BaseModel):
    name: str
    p: float
