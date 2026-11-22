"""Super Administrator simulation and audit schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SimulationCreate(BaseModel):
    """A Super Admin scenario definition to start in isolation."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=3, max_length=160)
    hazard_type: str = Field(min_length=2, max_length=64)
    area_name: str = Field(min_length=2, max_length=200)
    severity: str
    scenario_notes: str | None = Field(default=None, max_length=4000)

    @field_validator("name", "hazard_type", "area_name", "scenario_notes")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        if value not in {"low", "moderate", "high", "extreme"}:
            raise ValueError("Severity must be low, moderate, high, or extreme.")
        return value


class SimulationResponse(BaseModel):
    """Persisted simulation lifecycle and configuration."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    hazard_type: str
    area_name: str
    severity: str
    scenario_notes: str | None
    status: str
    started_by_user_id: UUID
    stopped_by_user_id: UUID | None
    started_at: datetime
    ended_at: datetime | None


class AdminAuditResponse(BaseModel):
    """Safe audit fields visible to Super Administrators."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: UUID | None
    actor_name: str
    action: str
    target_type: str
    target_id: str | None
    target_label: str | None
    details: dict
    created_at: datetime
