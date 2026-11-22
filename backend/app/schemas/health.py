"""Response schema for the health endpoint."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Simple liveness status."""

    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    """Database readiness status."""

    status: Literal["ready", "not_ready"]
    database: Literal["ok", "unavailable"]
