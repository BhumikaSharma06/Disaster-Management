"""Offline GeoJSON validation and quarantined dataset staging."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.dataset_import import DatasetImport, DatasetImportRecord
from app.schemas.dataset_import import (
    DatasetFeatureCollection,
    DatasetManifest,
)
from app.schemas.geography import (
    MultiPolygonGeometry,
    PointGeometry,
    RegionImport,
    ShelterImport,
)

logger = logging.getLogger(__name__)
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_GEOJSON_BYTES = 100 * 1024 * 1024


class DatasetValidationError(ValueError):
    """Raised when a source file cannot be safely parsed or validated."""


def _read_bounded(path: Path, maximum_bytes: int) -> bytes:
    try:
        with path.open("rb") as source_file:
            content = source_file.read(maximum_bytes + 1)
    except OSError as error:
        raise DatasetValidationError(f"Cannot read {path}: {error}") from error
    if len(content) > maximum_bytes:
        raise DatasetValidationError(f"{path.name} exceeds the {maximum_bytes}-byte size limit")
    return content


def load_manifest(path: Path) -> DatasetManifest:
    """Read and validate the metadata manifest."""
    content = _read_bounded(path, MAX_MANIFEST_BYTES)
    try:
        return DatasetManifest.model_validate_json(content)
    except ValidationError as error:
        raise DatasetValidationError(
            json.dumps(error.errors(include_input=False, include_context=False))
        ) from error


def load_feature_collection(path: Path) -> tuple[DatasetFeatureCollection, str]:
    """Read a bounded GeoJSON FeatureCollection and calculate its content hash."""
    content = _read_bounded(path, MAX_GEOJSON_BYTES)
    try:
        collection = DatasetFeatureCollection.model_validate_json(content)
    except ValidationError as error:
        raise DatasetValidationError(
            json.dumps(error.errors(include_input=False, include_context=False))
        ) from error
    return collection, hashlib.sha256(content).hexdigest()


def validate_features(
    manifest: DatasetManifest, collection: DatasetFeatureCollection
) -> tuple[list[tuple[str, dict[str, Any]]], list[dict[str, Any]]]:
    """Validate all feature properties and return normalized staged payloads."""
    valid_records: list[tuple[str, dict[str, Any]]] = []
    errors: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for index, feature in enumerate(collection.features):
        source_feature_id = str(feature.id)
        if source_feature_id in seen_ids:
            errors.append(
                {
                    "feature_index": index,
                    "feature_id": source_feature_id,
                    "error": "duplicate feature id",
                }
            )
            continue
        seen_ids.add(source_feature_id)

        payload = feature.model_dump(mode="json")
        properties = dict(feature.properties)
        reserved_metadata = {
            "source_name",
            "source_reference",
            "source_license",
            "verification_status",
            "verified_at",
            "verified_by",
        }
        conflicting_metadata = reserved_metadata.intersection(properties)
        if conflicting_metadata:
            errors.append(
                {
                    "feature_index": index,
                    "feature_id": source_feature_id,
                    "error": (
                        "provenance and verification fields belong in the manifest, "
                        f"not feature properties: {sorted(conflicting_metadata)}"
                    ),
                }
            )
            continue
        common_provenance = {
            "source_name": manifest.source_name,
            "source_reference": manifest.source_reference,
            "source_license": manifest.source_license,
        }
        try:
            if manifest.record_type == "regions":
                if not isinstance(feature.geometry, MultiPolygonGeometry):
                    raise ValueError("region feature geometry must be MultiPolygon")
                RegionImport.model_validate(
                    {
                        **properties,
                        "boundary": feature.geometry.model_dump(),
                        **common_provenance,
                    }
                )
            else:
                if not isinstance(feature.geometry, PointGeometry):
                    raise ValueError("shelter feature geometry must be Point")
                ShelterImport.model_validate(
                    {
                        **properties,
                        "location": feature.geometry.model_dump(),
                        **common_provenance,
                    }
                )
        except (ValidationError, ValueError) as error:
            if isinstance(error, ValidationError):
                detail: object = error.errors(include_input=False, include_context=False)
            else:
                detail = str(error)
            errors.append(
                {
                    "feature_index": index,
                    "feature_id": source_feature_id,
                    "error": detail,
                }
            )
            continue

        payload["properties"] = properties
        valid_records.append((source_feature_id, payload))

    return valid_records, errors


def _new_import(
    manifest: DatasetManifest,
    geojson_path: Path,
    content_sha256: str,
    record_count: int,
    validation_status: str,
    validation_report: dict[str, object],
) -> DatasetImport:
    """Build a dataset registry entry that cannot bypass review."""
    return DatasetImport(
        dataset_key=manifest.dataset_key,
        dataset_family=manifest.dataset_family,
        evidence_type=manifest.evidence_type,
        record_type=manifest.record_type,
        source_name=manifest.source_name,
        source_reference=manifest.source_reference,
        source_license=manifest.source_license,
        attribution=manifest.attribution,
        coverage=manifest.coverage,
        period_start=manifest.period_start,
        period_end=manifest.period_end,
        source_updated_at=manifest.source_updated_at,
        stale_after_days=manifest.stale_after_days,
        rights_status=manifest.rights_status,
        rights_reference=manifest.rights_reference,
        content_sha256=content_sha256,
        file_name=geojson_path.name[:255],
        record_count=record_count,
        validation_status=validation_status,
        validation_report=validation_report,
        review_status="pending",
        publication_status="quarantined",
    )


def stage_dataset(
    session: Session,
    manifest: DatasetManifest,
    geojson_path: Path,
    collection: DatasetFeatureCollection,
    content_sha256: str,
) -> tuple[DatasetImport, bool]:
    """Persist validated payloads in quarantine, or a failed quality report."""
    existing = session.scalar(
        select(DatasetImport).where(
            DatasetImport.dataset_key == manifest.dataset_key,
            DatasetImport.content_sha256 == content_sha256,
        )
    )
    if existing is not None:
        return existing, False

    valid_records, errors = validate_features(manifest, collection)
    validation_status = "failed" if errors else "passed"
    validation_report: dict[str, object] = {
        "feature_count": len(collection.features),
        "valid_feature_count": len(valid_records),
        "rejected_feature_count": len(errors),
        "errors": errors,
    }
    dataset_import = _new_import(
        manifest,
        geojson_path,
        content_sha256,
        len(valid_records) if not errors else 0,
        validation_status,
        validation_report,
    )
    session.add(dataset_import)
    session.flush()
    if not errors:
        session.add_all(
            [
                DatasetImportRecord(
                    dataset_import_id=dataset_import.id,
                    source_feature_id=source_id,
                    payload=payload,
                )
                for source_id, payload in valid_records
            ]
        )
    return dataset_import, True


def _write_report(path: Path | None, report: dict[str, object]) -> None:
    if path is None:
        return
    try:
        path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise DatasetValidationError(f"Cannot write report to {path}: {error}") from error


def main() -> int:
    """Validate a bundle, optionally staging it in the local database."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--geojson", type=Path, required=True)
    parser.add_argument(
        "--stage",
        action="store_true",
        help="Persist validated records in quarantine; otherwise only validate.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional path for a JSON validation report.",
    )
    arguments = parser.parse_args()

    try:
        manifest = load_manifest(arguments.manifest)
        collection, content_sha256 = load_feature_collection(arguments.geojson)
        valid_records, errors = validate_features(manifest, collection)
        report: dict[str, object] = {
            "dataset_key": manifest.dataset_key,
            "evidence_type": manifest.evidence_type,
            "file_name": arguments.geojson.name,
            "content_sha256": content_sha256,
            "feature_count": len(collection.features),
            "valid_feature_count": len(valid_records),
            "rejected_feature_count": len(errors),
            "validation_status": "failed" if errors else "passed",
            "review_status": "pending",
            "publication_status": "quarantined",
            "errors": errors,
        }
        _write_report(arguments.report, report)
        if errors and not arguments.stage:
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 2
        if not arguments.stage:
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0

        with SessionLocal.begin() as session:
            dataset_import, created = stage_dataset(
                session, manifest, arguments.geojson, collection, content_sha256
            )
            report["import_id"] = dataset_import.id
            report["already_staged"] = not created
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 2 if errors else 0
    except DatasetValidationError as error:
        logger.error("Dataset import validation failed: %s", error)
        print(json.dumps({"validation_status": "failed", "error": str(error)}))
        return 2
    except IntegrityError as error:
        logger.exception("Dataset import failed database constraints")
        print(json.dumps({"validation_status": "failed", "error": str(error.orig)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
