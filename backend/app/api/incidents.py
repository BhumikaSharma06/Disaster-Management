"""Incident registry and operator-updated emergency operations."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth import require_admin, require_responder_or_admin
from app.core.database import get_db
from app.models.incident import Incident, IncidentShelter
from app.models.shelter import Shelter
from app.models.sos_request import SOSRequest
from app.models.user import User
from app.schemas.incident import (
    IncidentCreate,
    IncidentShelterUpdate,
    IncidentStatusUpdate,
    SosCreate,
    SosStatusUpdate,
)
from app.services.coordination_rate_limit import enforce_submission_limit
from app.services.admin_audit import record_admin_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["incident operations"])


def _incident_payload(incident: Incident) -> dict:
    return {
        "id": incident.id,
        "title": incident.title,
        "hazard_type": incident.hazard_type,
        "area_name": incident.area_name,
        "description": incident.description,
        "status": incident.status,
        "created_at": incident.created_at,
        "updated_at": incident.updated_at,
    }


@router.get("/incidents")
def list_incidents(
    include_closed: bool = False,
    db: Session = Depends(get_db),
) -> list[dict]:
    """List active incidents for the dashboard's incident selector."""
    statement = select(Incident).order_by(Incident.created_at.desc(), Incident.id.desc())
    if not include_closed:
        statement = statement.where(Incident.status != "closed")
    try:
        return [_incident_payload(row) for row in db.scalars(statement).all()]
    except SQLAlchemyError as error:
        logger.exception("Could not retrieve incidents")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve incidents from the database.",
        ) from error


@router.post("/incidents", status_code=status.HTTP_201_CREATED)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> dict:
    """Create a named incident; only an administrator can open incidents."""
    incident = Incident(
        title=payload.title,
        hazard_type=payload.hazard_type,
        area_name=payload.area_name,
        description=payload.description,
        created_by_user_id=actor.id,
    )
    try:
        db.add(incident)
        db.flush()
        record_admin_action(
            db,
            actor,
            action="incident_created",
            target_type="incident",
            target_id=str(incident.id),
            target_label=incident.title,
            details={"hazard_type": incident.hazard_type, "area_name": incident.area_name},
        )
        db.commit()
        db.refresh(incident)
    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Could not create an incident")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to create the incident.",
        ) from error
    return _incident_payload(incident)


@router.patch("/incidents/{incident_id}")
def update_incident_status(
    incident_id: int,
    payload: IncidentStatusUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> dict:
    """Update an incident lifecycle state."""
    try:
        incident = db.get(Incident, incident_id)
    except SQLAlchemyError as error:
        logger.exception("Could not retrieve incident for status update")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve the incident.",
        ) from error
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    incident.status = payload.status
    incident.updated_by_user_id = actor.id
    incident.updated_at = datetime.now(UTC)
    try:
        record_admin_action(
            db,
            actor,
            action="incident_status_updated",
            target_type="incident",
            target_id=str(incident.id),
            target_label=incident.title,
            details={"status": incident.status},
        )
        db.commit()
        db.refresh(incident)
    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Could not update incident status")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to update incident status.",
        ) from error
    return _incident_payload(incident)


@router.get("/incidents/{incident_id}/operations")
def get_incident_operations(incident_id: int, db: Session = Depends(get_db)) -> dict:
    """Return one incident's SOS and shelter state with source timestamps."""
    try:
        incident = db.get(Incident, incident_id)
        if incident is None:
            raise HTTPException(status_code=404, detail="Incident not found.")
        sos_rows = (
            db.execute(
                select(
                    SOSRequest.id,
                    SOSRequest.need_type,
                    SOSRequest.description,
                    SOSRequest.urgency,
                    SOSRequest.status,
                    SOSRequest.people_affected,
                    SOSRequest.incident_id,
                    SOSRequest.created_at,
                    SOSRequest.updated_at,
                    func.ST_Y(SOSRequest.location).label("latitude"),
                    func.ST_X(SOSRequest.location).label("longitude"),
                )
                .where(SOSRequest.incident_id == incident_id)
                .order_by(SOSRequest.created_at.desc(), SOSRequest.id.desc())
            )
            .mappings()
            .all()
        )
        shelter_rows = (
            db.execute(
                select(
                    Shelter.id,
                    Shelter.name,
                    Shelter.capacity,
                    Shelter.source_name,
                    func.ST_Y(Shelter.location).label("latitude"),
                    func.ST_X(Shelter.location).label("longitude"),
                    IncidentShelter.operational_status,
                    IncidentShelter.current_occupancy,
                    IncidentShelter.update_note,
                    IncidentShelter.updated_at,
                )
                .join(IncidentShelter, IncidentShelter.shelter_id == Shelter.id)
                .where(IncidentShelter.incident_id == incident_id)
                .order_by(Shelter.name, Shelter.id)
            )
            .mappings()
            .all()
        )
        available_shelter_rows = (
            db.execute(
                select(
                    Shelter.id,
                    Shelter.name,
                    Shelter.capacity,
                    Shelter.source_name,
                    Shelter.verification_status,
                    func.ST_Y(Shelter.location).label("latitude"),
                    func.ST_X(Shelter.location).label("longitude"),
                )
                .outerjoin(
                    IncidentShelter,
                    (IncidentShelter.shelter_id == Shelter.id)
                    & (IncidentShelter.incident_id == incident_id),
                )
                .where(IncidentShelter.id.is_(None))
                .order_by(Shelter.name, Shelter.id)
            )
            .mappings()
            .all()
        )
    except SQLAlchemyError as error:
        logger.exception("Could not retrieve incident operations")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve live incident operations.",
        ) from error

    sos = [dict(row) for row in sos_rows]
    shelters = [
        {
            "id": row["id"],
            "name": row["name"],
            "capacity": row["capacity"],
            "source_name": row["source_name"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "operational_status": row["operational_status"],
            "current_occupancy": row["current_occupancy"],
            "update_note": row["update_note"],
            "updated_at": row["updated_at"],
        }
        for row in shelter_rows
    ]
    available_shelters = [dict(row) for row in available_shelter_rows]
    return {
        "incident": _incident_payload(incident),
        "sos": sos,
        "shelters": shelters,
        "available_shelters": available_shelters,
        "fetched_at": datetime.now(UTC),
        "source": "operator-and-citizen-submitted-records",
    }


@router.put("/incidents/{incident_id}/shelters/{shelter_id}")
def update_incident_shelter(
    incident_id: int,
    shelter_id: int,
    payload: IncidentShelterUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_responder_or_admin),
) -> dict:
    """Record responder-verified shelter status and occupancy for an incident."""
    try:
        incident = db.get(Incident, incident_id)
        shelter = db.get(Shelter, shelter_id)
        record = db.scalar(
            select(IncidentShelter).where(
                IncidentShelter.incident_id == incident_id,
                IncidentShelter.shelter_id == shelter_id,
            )
        )
    except SQLAlchemyError as error:
        logger.exception("Could not retrieve incident shelter state")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve incident shelter operations.",
        ) from error
    if incident is None or incident.status == "closed":
        raise HTTPException(status_code=404, detail="Active incident not found.")
    if shelter is None:
        raise HTTPException(status_code=404, detail="Shelter not found.")
    if (
        payload.current_occupancy is not None
        and shelter.capacity is not None
        and payload.current_occupancy > shelter.capacity
    ):
        raise HTTPException(
            status_code=422,
            detail="Reported occupancy cannot exceed the shelter's registered capacity.",
        )
    if record is None:
        record = IncidentShelter(
            incident_id=incident_id,
            shelter_id=shelter_id,
            updated_by_user_id=actor.id,
        )
        db.add(record)
    record.operational_status = payload.operational_status
    record.current_occupancy = payload.current_occupancy
    record.update_note = payload.update_note
    record.updated_by_user_id = actor.id
    record.updated_at = datetime.now(UTC)
    try:
        db.commit()
        db.refresh(record)
    except IntegrityError as error:
        db.rollback()
        logger.exception("Shelter operational update conflicted")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shelter operational update conflicted with another update. Refresh and retry.",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Could not update incident shelter state")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to update shelter operations.",
        ) from error
    return {
        "incident_id": incident_id,
        "shelter_id": shelter_id,
        "operational_status": record.operational_status,
        "current_occupancy": record.current_occupancy,
        "update_note": record.update_note,
        "updated_at": record.updated_at,
    }


@router.post("/sos", status_code=status.HTTP_201_CREATED)
def create_sos_request(
    payload: SosCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Accept an idempotent, throttled citizen SOS submission."""
    try:
        existing = db.scalar(
            select(SOSRequest).where(
                SOSRequest.client_submission_id == payload.client_submission_id
            )
        )
    except SQLAlchemyError as error:
        logger.exception("Could not check SOS submission idempotency")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to submit SOS right now. Please retry.",
        ) from error
    if existing is not None:
        return {"id": existing.id, "status": existing.status, "created_at": existing.created_at}
    if payload.incident_id is not None:
        try:
            incident = db.get(Incident, payload.incident_id)
        except SQLAlchemyError as error:
            logger.exception("Could not verify incident for SOS submission")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to verify the selected incident.",
            ) from error
        if incident is None or incident.status == "closed":
            raise HTTPException(status_code=404, detail="Active incident not found.")
    try:
        enforce_submission_limit(request, db, "sos")
    except SQLAlchemyError as error:
        logger.exception("Could not apply SOS submission rate limit")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to submit SOS right now. Please retry.",
        ) from error
    record = SOSRequest(
        incident_id=payload.incident_id,
        client_submission_id=payload.client_submission_id,
        need_type=payload.need_type,
        description=payload.description,
        urgency=payload.urgency,
        people_affected=payload.people_affected,
        location=WKTElement(f"POINT({payload.longitude} {payload.latitude})", srid=4326),
    )
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except IntegrityError as error:
        db.rollback()
        duplicate = db.scalar(
            select(SOSRequest).where(
                SOSRequest.client_submission_id == payload.client_submission_id
            )
        )
        if duplicate is not None:
            return {
                "id": duplicate.id,
                "status": duplicate.status,
                "created_at": duplicate.created_at,
            }
        logger.exception("SOS submission conflicted")
        raise HTTPException(status_code=409, detail="SOS submission could not be saved.") from error
    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Could not save SOS submission")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to submit SOS right now. Please retry.",
        ) from error
    return {"id": record.id, "status": record.status, "created_at": record.created_at}


@router.patch("/incidents/{incident_id}/sos/{sos_id}")
def update_sos_status(
    incident_id: int,
    sos_id: int,
    payload: SosStatusUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_responder_or_admin),
) -> dict:
    """Record responder acknowledgement or resolution of an incident SOS."""
    try:
        record = db.scalar(
            select(SOSRequest).where(
                SOSRequest.id == sos_id,
                SOSRequest.incident_id == incident_id,
            )
        )
    except SQLAlchemyError as error:
        logger.exception("Could not retrieve incident SOS request")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve the incident SOS request.",
        ) from error
    if record is None:
        raise HTTPException(status_code=404, detail="Incident SOS request not found.")
    record.status = payload.status
    record.updated_by_user_id = actor.id
    record.updated_at = datetime.now(UTC)
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Could not update SOS status")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to update SOS status.",
        ) from error
    return {"id": record.id, "status": record.status, "updated_at": record.updated_at}
