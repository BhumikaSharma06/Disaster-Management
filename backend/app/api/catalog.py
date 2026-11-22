"""Read-only endpoints for regions and shelters."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.dataset_import import DatasetImport
from app.models.region import Region
from app.models.shelter import Shelter
from app.schemas.dataset_import import DatasetImportResponse
from app.schemas.geography import RegionResponse, ShelterResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/regions", response_model=list[RegionResponse])
def list_regions(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[RegionResponse]:
    """List administrative regions with their GeoJSON boundaries."""
    statement = (
        select(
            Region.id,
            Region.name,
            Region.region_type,
            Region.district_name,
            Region.parent_id,
            func.ST_AsGeoJSON(Region.boundary).label("boundary"),
            Region.source_name,
            Region.source_reference,
            Region.source_license,
            Region.verification_status,
            Region.verified_at,
            Region.verified_by,
        )
        .order_by(Region.id)
        .limit(limit)
        .offset(offset)
    )
    try:
        rows = db.execute(statement).mappings().all()
    except SQLAlchemyError as error:
        logger.exception("Could not retrieve regions")
        raise HTTPException(
            status_code=503, detail="Unable to retrieve regions from the database"
        ) from error

    return [
        RegionResponse.model_validate({**row, "boundary": json.loads(row["boundary"])})
        for row in rows
    ]


@router.get("/shelters", response_model=list[ShelterResponse])
def list_shelters(
    region_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[ShelterResponse]:
    """List shelters, optionally filtered by administrative region."""
    statement = select(
        Shelter.id,
        Shelter.name,
        Shelter.region_id,
        Shelter.capacity,
        Shelter.current_occupancy,
        func.ST_AsGeoJSON(Shelter.location).label("location"),
        Shelter.source_name,
        Shelter.source_reference,
        Shelter.source_license,
        Shelter.verification_status,
        Shelter.verified_at,
        Shelter.verified_by,
    )
    if region_id is not None:
        statement = statement.where(Shelter.region_id == region_id)
    statement = statement.order_by(Shelter.id).limit(limit).offset(offset)

    try:
        rows = db.execute(statement).mappings().all()
    except SQLAlchemyError as error:
        logger.exception("Could not retrieve shelters")
        raise HTTPException(
            status_code=503, detail="Unable to retrieve shelters from the database"
        ) from error

    return [
        ShelterResponse.model_validate({**row, "location": json.loads(row["location"])})
        for row in rows
    ]


@router.get("/datasets", response_model=list[DatasetImportResponse])
def list_dataset_imports(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[DatasetImportResponse]:
    """List dataset provenance and review metadata without exposing staged data."""
    statement = (
        select(DatasetImport)
        .order_by(DatasetImport.imported_at.desc(), DatasetImport.id.desc())
        .limit(limit)
        .offset(offset)
    )
    try:
        imports = db.scalars(statement).all()
    except SQLAlchemyError as error:
        logger.exception("Could not retrieve dataset imports")
        raise HTTPException(
            status_code=503, detail="Unable to retrieve dataset imports from the database"
        ) from error
    return [DatasetImportResponse.from_import(dataset_import) for dataset_import in imports]
