"""Tests for geography import validation and verification metadata."""

import pytest
from pydantic import ValidationError

from app.schemas.geography import (
    MultiPolygonGeometry,
    PointGeometry,
    RegionImport,
    RegionResponse,
    ShelterImport,
    ShelterResponse,
)

BOUNDARY = {
    "type": "MultiPolygon",
    "coordinates": [
        [
            [
                [86.0, 25.0],
                [87.0, 25.0],
                [87.0, 26.0],
                [86.0, 26.0],
                [86.0, 25.0],
            ]
        ]
    ],
}


def test_import_contract_requires_provenance_and_defaults_unverified() -> None:
    region = RegionImport(
        name=" Example area ",
        region_type="district",
        district_name="Example district",
        boundary=BOUNDARY,
        source_name=" Example dataset ",
    )
    shelter = ShelterImport(
        name="Example shelter",
        location={"type": "Point", "coordinates": [86.5, 25.5]},
        source_name="Example dataset",
    )

    assert region.name == "Example area"
    assert region.source_name == "Example dataset"
    assert shelter.model_dump()["source_name"] == "Example dataset"
    assert "verification_status" not in region.model_dump()
    assert "verified_at" not in shelter.model_dump()


@pytest.mark.parametrize(
    "coordinates",
    [
        [181, 25],
        [86, 91],
        [float("nan"), 25],
        [86],
    ],
)
def test_point_import_rejects_invalid_coordinates(coordinates: list[float]) -> None:
    with pytest.raises(ValidationError):
        PointGeometry(type="Point", coordinates=coordinates)


@pytest.mark.parametrize(
    "coordinates",
    [
        [],
        [[[[86, 25], [87, 25], [87, 26]]]],
        [[[[86, 25], [87, 25], [87, 26], [86, 26]]]],
        [[[[86, 25], [87, 25], [87, 26], [86, 26], [86, 25.5]]]],
        [[[[86, 25], [181, 25], [87, 26], [86, 26], [86, 25]]]],
    ],
)
def test_multipolygon_import_rejects_invalid_rings(
    coordinates: list[list[list[list[float]]]],
) -> None:
    with pytest.raises(ValidationError):
        MultiPolygonGeometry(type="MultiPolygon", coordinates=coordinates)


@pytest.mark.parametrize(
    "payload",
    [
        {
            "name": " ",
            "source_name": "dataset",
            "location": {"type": "Point", "coordinates": [0, 0]},
        },
        {
            "name": "Shelter",
            "source_name": " ",
            "location": {"type": "Point", "coordinates": [0, 0]},
        },
        {
            "name": "Shelter",
            "source_name": "dataset",
            "verification_status": "verified",
            "location": {"type": "Point", "coordinates": [0, 0]},
        },
        {
            "name": "Shelter",
            "source_name": "dataset",
            "capacity": 0,
            "location": {"type": "Point", "coordinates": [0, 0]},
        },
    ],
)
def test_shelter_import_rejects_invalid_or_untrusted_fields(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ShelterImport(**payload)


def test_verified_response_requires_reviewer_time_and_source() -> None:
    base = {
        "id": 1,
        "name": "Example shelter",
        "region_id": None,
        "capacity": 20,
        "current_occupancy": 1,
        "location": {"type": "Point", "coordinates": [86.5, 25.5]},
        "source_name": "Example dataset",
        "source_reference": None,
        "source_license": None,
        "verification_status": "verified",
    }

    with pytest.raises(ValidationError):
        ShelterResponse(**base, verified_at=None, verified_by=None)

    verified = ShelterResponse(
        **base,
        verified_at="2026-11-19T10:00:00Z",
        verified_by="reviewer@example.invalid",
    )
    assert verified.verification_status == "verified"


def test_legacy_record_cannot_be_marked_verified() -> None:
    with pytest.raises(ValidationError):
        RegionResponse(
            id=1,
            name="Legacy area",
            region_type="district",
            district_name="Example district",
            parent_id=None,
            boundary=BOUNDARY,
            source_name="Unspecified (legacy record)",
            source_reference=None,
            verification_status="verified",
            verified_at="2026-11-19T10:00:00Z",
            verified_by="reviewer",
        )
