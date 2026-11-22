"""Contracts for incident operations and citizen SOS submissions."""

import math
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class IncidentCreate(BaseModel):
    """Create an operator-managed incident."""

    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, Field(min_length=1, max_length=160)]
    hazard_type: Annotated[str, Field(min_length=1, max_length=40)]
    area_name: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str | None, Field(max_length=4000)] = None

    @field_validator("title", "hazard_type", "area_name")
    @classmethod
    def trim_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field must not be blank.")
        return normalized

    @field_validator("description")
    @classmethod
    def trim_description(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class IncidentStatusUpdate(BaseModel):
    """Change an incident's operational lifecycle."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["active", "monitoring", "closed"]


class IncidentShelterUpdate(BaseModel):
    """Operator-reported shelter state scoped to a single incident."""

    model_config = ConfigDict(extra="forbid")

    operational_status: Literal["unknown", "open", "limited", "closed"]
    current_occupancy: Annotated[int | None, Field(ge=0, le=10_000_000)] = None
    update_note: Annotated[str | None, Field(max_length=500)] = None

    @field_validator("update_note")
    @classmethod
    def trim_note(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class SosCreate(BaseModel):
    """A geolocated help request with an optional active incident association."""

    model_config = ConfigDict(extra="forbid")

    client_submission_id: uuid.UUID
    incident_id: Annotated[int | None, Field(gt=0)] = None
    need_type: Annotated[str, Field(min_length=1, max_length=64)]
    description: Annotated[str, Field(min_length=1, max_length=4000)]
    urgency: Literal["urgent", "high", "general"] = "high"
    people_affected: Annotated[int | None, Field(ge=1, le=100_000)] = None
    latitude: Annotated[float, Field(ge=-90, le=90)]
    longitude: Annotated[float, Field(ge=-180, le=180)]

    @field_validator("need_type", "description")
    @classmethod
    def trim_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field must not be blank.")
        return normalized

    @model_validator(mode="after")
    def validate_coordinates(self) -> "SosCreate":
        if not math.isfinite(self.latitude) or not math.isfinite(self.longitude):
            raise ValueError("Coordinates must be finite.")
        return self


class SosStatusUpdate(BaseModel):
    """Responder update for an SOS case."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["open", "acknowledged", "resolved", "closed"]
