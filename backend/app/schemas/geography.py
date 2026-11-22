"""Response schemas for geographic catalog data."""

import math
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Position = tuple[float, float]
SourceName = Annotated[str, Field(min_length=1, max_length=200)]
SourceReference = Annotated[str | None, Field(max_length=500)]


def _validate_position(position: Position) -> Position:
    longitude, latitude = position
    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise ValueError("longitude must be finite and between -180 and 180")
    if not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise ValueError("latitude must be finite and between -90 and 90")
    return position


class PointGeometry(BaseModel):
    """GeoJSON point geometry in longitude, latitude order."""

    type: Literal["Point"]
    coordinates: Position

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, coordinates: Position) -> Position:
        return _validate_position(coordinates)


class MultiPolygonGeometry(BaseModel):
    """GeoJSON multipolygon geometry in longitude, latitude order."""

    type: Literal["MultiPolygon"]
    coordinates: list[list[list[Position]]]

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(
        cls, coordinates: list[list[list[Position]]]
    ) -> list[list[list[Position]]]:
        if not coordinates:
            raise ValueError("multipolygon must contain at least one polygon")
        for polygon in coordinates:
            if not polygon:
                raise ValueError("polygon must contain at least one linear ring")
            for ring in polygon:
                if len(ring) < 4:
                    raise ValueError("linear ring must contain at least four positions")
                if ring[0] != ring[-1]:
                    raise ValueError("linear ring must be closed")
                for position in ring:
                    _validate_position(position)
        return coordinates


class ProvenanceFields(BaseModel):
    """Source and review metadata shared by catalog records."""

    source_name: SourceName
    source_reference: SourceReference = None
    source_license: Annotated[str | None, Field(max_length=200)] = None
    verification_status: Literal["unverified", "verified"]
    verified_at: datetime | None
    verified_by: Annotated[str | None, Field(max_length=160)]

    @field_validator("source_name")
    @classmethod
    def trim_source_name(cls, source_name: str) -> str:
        normalized = source_name.strip()
        if not normalized:
            raise ValueError("source_name must not be blank")
        return normalized

    @field_validator("verified_by")
    @classmethod
    def trim_verified_by(cls, verified_by: str | None) -> str | None:
        if verified_by is None:
            return None
        return verified_by.strip() or None

    @model_validator(mode="after")
    def validate_verification_evidence(self) -> "ProvenanceFields":
        if self.verification_status == "verified":
            if not self.verified_at or not self.verified_by or not self.verified_by.strip():
                raise ValueError("verified records require a reviewer and timestamp")
            if self.verified_at.tzinfo is None or self.verified_at.utcoffset() is None:
                raise ValueError("verified_at must include a timezone")
            if self.source_name == "Unspecified (legacy record)":
                raise ValueError("legacy records cannot be marked verified")
        elif self.verified_at is not None or self.verified_by is not None:
            raise ValueError("review evidence is only valid for verified records")
        return self


class RegionResponse(ProvenanceFields):
    """Administrative region with its boundary geometry."""

    id: int
    name: str
    region_type: str
    district_name: str
    parent_id: int | None
    boundary: MultiPolygonGeometry


class ShelterResponse(ProvenanceFields):
    """Shelter capacity and mapped location."""

    id: int
    name: str
    region_id: int | None
    capacity: int | None
    current_occupancy: int
    location: PointGeometry


class RegionImport(BaseModel):
    """Validated import contract; imports are always unverified."""

    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=160)]
    region_type: Annotated[str, Field(min_length=1, max_length=32)]
    district_name: Annotated[str, Field(min_length=1, max_length=120)]
    parent_id: int | None = Field(default=None, ge=1)
    boundary: MultiPolygonGeometry
    source_name: SourceName
    source_reference: SourceReference = None
    source_license: Annotated[str | None, Field(max_length=200)] = None

    @field_validator("name", "region_type", "district_name", "source_name")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized


class ShelterImport(BaseModel):
    """Validated shelter import contract; imports are always unverified."""

    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=160)]
    region_id: int | None = Field(default=None, ge=1)
    capacity: int | None = Field(default=None, gt=0)
    current_occupancy: int = Field(default=0, ge=0)
    location: PointGeometry
    source_name: SourceName
    source_reference: SourceReference = None
    source_license: Annotated[str | None, Field(max_length=200)] = None

    @field_validator("name", "source_name")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized
