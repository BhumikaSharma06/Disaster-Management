"""Response schema for the health endpoint."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Simple liveness status."""

    status: Literal["ok"]
