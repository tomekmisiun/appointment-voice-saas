from typing import Literal

from pydantic import BaseModel


HealthState = Literal["ok", "unavailable"]


class HealthStatus(BaseModel):
    status: HealthState


class DependencyHealth(BaseModel):
    status: HealthState
    message: str | None = None


class ReadinessHealth(BaseModel):
    status: HealthState
    checks: dict[str, DependencyHealth]
