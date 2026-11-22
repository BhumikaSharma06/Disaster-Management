"""Tests for dataset metadata contracts and quarantined GeoJSON validation."""

from collections.abc import Iterator
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.database import get_db
from app.main import app
from app.schemas.dataset_import import (
    DatasetFeatureCollection,
    DatasetImportResponse,
    DatasetManifest,
)
from app.services.import_dataset import validate_features

client = TestClient(app)

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


def _region_manifest(**overrides: object) -> DatasetManifest:
    values: dict[str, object] = {
        "dataset_key": "test-regions",
        "dataset_family": "administrative_geography",
        "evidence_type": "geography",
        "record_type": "regions",
        "source_name": "SYNTHETIC test fixture",
        "coverage": "SYNTHETIC test area",
    }
    return DatasetManifest(**(values | overrides))


def _feature_collection(features: list[dict[str, object]]) -> DatasetFeatureCollection:
    return DatasetFeatureCollection(type="FeatureCollection", features=features)


def _region_feature(
    feature_id: str = "region-1", *, properties: dict[str, object] | None = None
) -> dict[str, object]:
    return {
        "type": "Feature",
        "id": feature_id,
        "geometry": BOUNDARY,
        "properties": properties
        or {
            "name": "SYNTHETIC region",
            "region_type": "district",
            "district_name": "SYNTHETIC",
        },
    }


def test_manifest_requires_consistent_family_and_documented_rights_reference() -> None:
    with pytest.raises(ValidationError):
        _region_manifest(record_type="shelters")

    with pytest.raises(ValidationError):
        _region_manifest(rights_status="documented")

    manifest = _region_manifest(
        rights_status="documented",
        rights_reference="SYNTHETIC approval record",
    )
    assert manifest.rights_status == "documented"


def test_import_validation_keeps_records_unmodified_and_source_metadata_separate() -> None:
    manifest = _region_manifest(source_reference="SYNTHETIC source record")
    collection = _feature_collection([_region_feature()])

    valid, errors = validate_features(manifest, collection)

    assert errors == []
    assert len(valid) == 1
    feature_id, payload = valid[0]
    assert feature_id == "region-1"
    assert payload["properties"]["name"] == "SYNTHETIC region"
    assert "source_name" not in payload["properties"]
    assert manifest.source_name == "SYNTHETIC test fixture"


def test_import_validation_rejects_bad_properties_geometry_and_duplicate_ids() -> None:
    manifest = _region_manifest()
    collection = _feature_collection(
        [
            _region_feature(),
            _region_feature(
                "region-2",
                properties={
                    "name": " ",
                    "region_type": "district",
                    "district_name": "SYNTHETIC",
                },
            ),
            {
                **_region_feature("region-3"),
                "geometry": {"type": "Point", "coordinates": [86.5, 25.5]},
            },
            _region_feature(),
        ]
    )

    valid, errors = validate_features(manifest, collection)

    assert len(valid) == 1
    assert len(errors) == 3
    assert errors[0]["feature_id"] == "region-2"
    assert errors[1]["feature_id"] == "region-3"
    assert errors[2]["error"] == "duplicate feature id"


def test_import_rejects_unexpected_source_claims_in_feature_properties() -> None:
    manifest = _region_manifest()
    collection = _feature_collection(
        [
            _region_feature(
                properties={
                    "name": "SYNTHETIC region",
                    "region_type": "district",
                    "district_name": "SYNTHETIC",
                    "source_name": "SYNTHETIC claimed source",
                }
            )
        ]
    )

    valid, errors = validate_features(manifest, collection)

    assert valid == []
    assert len(errors) == 1


def test_dataset_registry_freshness_is_unknown_without_a_source_time_or_interval() -> None:
    imported_at = datetime(2026, 11, 19, 10, tzinfo=timezone.utc)
    record = SimpleNamespace(
        id=1,
        dataset_key="test-regions",
        dataset_family="administrative_geography",
        record_type="regions",
        source_name="SYNTHETIC test fixture",
        source_reference=None,
        source_license=None,
        attribution=None,
        coverage="SYNTHETIC test area",
        period_start=None,
        period_end=None,
        source_updated_at=None,
        stale_after_days=7,
        rights_status="unconfirmed",
        rights_reference=None,
        content_sha256="a" * 64,
        file_name="SYNTHETIC.geojson",
        record_count=1,
        evidence_type="geography",
        validation_status="passed",
        validation_report={"feature_count": 1},
        review_status="pending",
        reviewed_at=None,
        reviewed_by=None,
        publication_status="quarantined",
        imported_at=imported_at,
    )

    response = DatasetImportResponse.from_import(record, now=imported_at)

    assert response.freshness_status == "unknown"
    assert response.review_status == "pending"
    assert response.publication_status == "quarantined"


def test_dataset_registry_marks_expired_data_stale() -> None:
    imported_at = datetime(2026, 11, 19, 10, tzinfo=timezone.utc)
    record = SimpleNamespace(
        id=1,
        dataset_key="test-regions",
        dataset_family="administrative_geography",
        record_type="regions",
        source_name="SYNTHETIC test fixture",
        source_reference=None,
        source_license=None,
        attribution=None,
        coverage="SYNTHETIC test area",
        period_start=None,
        period_end=None,
        source_updated_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        stale_after_days=7,
        rights_status="unconfirmed",
        rights_reference=None,
        content_sha256="b" * 64,
        file_name="SYNTHETIC.geojson",
        record_count=1,
        evidence_type="geography",
        validation_status="passed",
        validation_report={"feature_count": 1},
        review_status="pending",
        reviewed_at=None,
        reviewed_by=None,
        publication_status="quarantined",
        imported_at=imported_at,
    )

    response = DatasetImportResponse.from_import(
        record, now=datetime(2026, 11, 19, 10, tzinfo=timezone.utc)
    )

    assert response.freshness_status == "stale"


class _ScalarResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


class _DatasetSession:
    def __init__(self, record: object) -> None:
        self.record = record

    def scalars(self, statement: Any) -> _ScalarResult:
        return _ScalarResult([self.record])


def test_dataset_registry_api_exposes_metadata_only_and_paginates() -> None:
    imported_at = datetime(2026, 11, 19, 10, tzinfo=timezone.utc)
    record = SimpleNamespace(
        id=19,
        dataset_key="test-regions",
        dataset_family="administrative_geography",
        record_type="regions",
        source_name="SYNTHETIC test fixture",
        source_reference="fixture record",
        source_license="test-only",
        attribution=None,
        coverage="SYNTHETIC test area",
        period_start=None,
        period_end=None,
        source_updated_at=None,
        stale_after_days=None,
        rights_status="unconfirmed",
        rights_reference=None,
        content_sha256="c" * 64,
        file_name="SYNTHETIC.geojson",
        record_count=1,
        evidence_type="geography",
        validation_status="passed",
        validation_report={
            "feature_count": 1,
            "rejected_feature_count": 1,
            "errors": [{"feature_id": "SYNTHETIC private detail"}],
        },
        review_status="pending",
        reviewed_at=None,
        reviewed_by=None,
        publication_status="quarantined",
        imported_at=imported_at,
    )
    session = _DatasetSession(record)

    def override_get_db() -> Iterator[_DatasetSession]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/api/datasets", params={"limit": 1, "offset": 2})
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == 19
    assert body[0]["review_status"] == "pending"
    assert body[0]["publication_status"] == "quarantined"
    assert body[0]["validation_report"]["rejected_feature_count"] == 1
    assert "errors" not in body[0]["validation_report"]
    assert "records" not in body[0]
