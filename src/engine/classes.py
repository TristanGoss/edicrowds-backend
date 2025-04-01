from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SensorType(StrEnum):
    CEC_PED_FLUX_COUNTER = 'City of Edinburgh Council Pedestrian Flux Counter'
    EE_PED_FLUX_COUNTER = 'Essential Edinburgh Pedestrian Flux Counter'


@dataclass(frozen=True, kw_only=True)
class Measurement:
    sensor_name: str
    datetime: datetime


@dataclass(frozen=True, kw_only=True)
class PedFluxCounterMeasurement(Measurement):
    flow_pax_per_hour: int
