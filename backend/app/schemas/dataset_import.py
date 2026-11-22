"""Shared dataset provenance and GeoJSON staging contracts."""

from datetime import date, datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.dataset_import import DatasetImport
from app.schemas.geography import MultiPolygonGeometry, PointGeometry

DatasetFamily = Literal[
    "administrative_geography",
    "exposure",
    "hazard_observations",
    "official_warnings",
    "flood_extent",
    "response_resources",
    "road_network",
    "community_reports",
    "safety_guidance",
    "model_outputs",
    "other",
]
EvidenceType = Literal[
    "geography",
    "exposure",
    "observation",
    "official_warning",
    "forecast",
    "resource_listing",
    "event_report",
    "community_report",
    "guidance",
    "model_output",
    "road_network",
    "other",
]
RecordType = Literal["regions", "shelters"]
DatasetKey = Annotated[
    str,
    Field(
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9._-]+$",
    ),
]


class DatasetManifest(BaseModel):
    """Source and lifecycle metadata supplied with a local dataset file."""

    model_config = ConfigDict(extra="forbid")

    dataset_key: DatasetKey
    dataset_family: DatasetFamily
    evidence_type: EvidenceType
    record_type: RecordType
    source_name: Annotated[str, Field(min_length=1, max_length=200)]
    source_reference: Annotated[str | None, Field(max_length=500)] = None
    source_license: Annotated[str | None, Field(max_length=200)] = None
    attribution: Annotated[str | None, Field(max_length=500)] = None
    coverage: Annotated[str, Field(min_length=1, max_length=500)]
    period_start: date | None = None
    period_end: date | None = None
    source_updated_at: datetime | None = None
    stale_after_days: int | None = Field(default=None, gt=0, le=3650)
    rights_status: Literal["unconfirmed", "documented"] = "unconfirmed"
    rights_reference: Annotated[str | None, Field(max_length=500)] = None

    @field_validator("dataset_key", "source_name", "coverage")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized

    @model_validator(mode="after")
    def validate_dataset_metadata(self) -> "DatasetManifest":
        if self.record_type == "regions" and (
            self.dataset_family != "administrative_geography" or self.evidence_type != "geography"
        ):
            raise ValueError("region imports must be administrative geography")
        if self.record_type == "shelters" and (
            self.dataset_family != "response_resources" or self.evidence_type != "resource_listing"
        ):
            raise ValueError("shelter imports must be response resource listings")
        if self.period_start and self.period_end and self.period_start > self.period_end:
            raise ValueError("period_start must not be later than period_end")
        if self.source_updated_at is not None and (
            self.source_updated_at.tzinfo is None or self.source_updated_at.utcoffset() is None
        ):
            raise ValueError("source_updated_at must include a timezone")
        if self.rights_status == "documented":
            if not self.rights_reference or not self.rights_reference.strip():
                raise ValueError("documented rights require a reference to the terms or approval")
        elif self.rights_reference is not None:
            raise ValueError(
                "rights_reference can only be supplied when rights_status is documented"
            )
        return self


class DatasetFeature(BaseModel):
    """One GeoJSON feature with a stable source identifier."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["Feature"]
    id: str | Annotated[int, Field(ge=0)]
    geometry: PointGeometry | MultiPolygonGeometry
    properties: dict[str, object]

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str | int) -> str | int:
        if isinstance(value, str) and not value.strip():
            raise ValueError("feature id must not be blank")
        if isinstance(value, str) and len(value) > 200:
            raise ValueError("feature id must be at most 200 characters")
        return value


class DatasetFeatureCollection(BaseModel):
    """Bounded GeoJSON FeatureCollection accepted by the staging importer."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["FeatureCollection"]
    features: Annotated[list[DatasetFeature], Field(min_length=1, max_length=50000)]


class DatasetImportResponse(BaseModel):
    """Read-only registry view; staged feature payloads are never exposed."""

    id: int
    dataset_key: str
    dataset_family: DatasetFamily
    evidence_type: EvidenceType
    record_type: RecordType
    source_name: str
    source_reference: str | None
    source_license: str | None
    attribution: str | None
    coverage: str
    period_start: date | None
    period_end: date | None
    source_updated_at: datetime | None
    stale_after_days: int | None
    freshness_status: Literal["fresh", "stale", "unknown"]
    rights_status: Literal["unconfirmed", "documented"]
    rights_reference: str | None
    content_sha256: str
    file_name: str
    record_count: int
    validation_status: Literal["passed", "failed"]
    validation_report: dict[str, object]
    review_status: Literal["pending", "approved", "rejected"]
    reviewed_at: datetime | None
    reviewed_by: str | None
    publication_status: Literal["quarantined", "published", "withdrawn"]
    imported_at: datetime

    @classmethod
    def from_import(
        cls, dataset_import: DatasetImport, *, now: datetime | None = None
    ) -> "DatasetImportResponse":
        """Create registry response with freshness derived from source time."""
        source_updated_at = dataset_import.source_updated_at
        stale_after_days = dataset_import.stale_after_days
        current_time = now or datetime.now(timezone.utc)
        if source_updated_at is None or stale_after_days is None:
            freshness_status = "unknown"
        else:
            age_seconds = (current_time - source_updated_at).total_seconds()
            freshness_status = "stale" if age_seconds > stale_after_days * 86400 else "fresh"
        return cls(
            id=dataset_import.id,
            dataset_key=dataset_import.dataset_key,
            dataset_family=dataset_import.dataset_family,
            evidence_type=dataset_import.evidence_type,
            record_type=dataset_import.record_type,
            source_name=dataset_import.source_name,
            source_reference=dataset_import.source_reference,
            source_license=dataset_import.source_license,
            attribution=dataset_import.attribution,
            coverage=dataset_import.coverage,
            period_start=dataset_import.period_start,
            period_end=dataset_import.period_end,
            source_updated_at=source_updated_at,
            stale_after_days=stale_after_days,
            freshness_status=freshness_status,
            rights_status=dataset_import.rights_status,
            rights_reference=dataset_import.rights_reference,
            content_sha256=dataset_import.content_sha256,
            file_name=dataset_import.file_name,
            record_count=dataset_import.record_count,
            validation_status=dataset_import.validation_status,
            validation_report={
                key: value
                for key, value in dataset_import.validation_report.items()
                if key != "errors"
            },
            review_status=dataset_import.review_status,
            reviewed_at=dataset_import.reviewed_at,
            reviewed_by=dataset_import.reviewed_by,
            publication_status=dataset_import.publication_status,
            imported_at=dataset_import.imported_at,
        )
