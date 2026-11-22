"""V1 endpoints for live forecasts, shelters, routes, alerts, and status."""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.hazards.registry import registry
from app.models.shelter import Shelter
from app.models.sos_request import SOSRequest
from app.services.geocoding import reverse_geocode, search_places
from app.services.live_data import live_data
from app.services.routing import evacuate_route, haversine_km, nearest_shelters
from app.services.translation import SUPPORTED_LANGUAGES, translation_service

router = APIRouter(prefix="/api/v1", tags=["AapdaSetu core"])
logger = logging.getLogger(__name__)


@router.get("/geocode")
async def geocode_place(
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(default=5, ge=1, le=10),
) -> dict:
    """Search Indian district/place names and return coordinates."""
    return await search_places(q, limit)


@router.get("/geocode/reverse")
async def reverse_geocode_place(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
) -> dict:
    """Resolve coordinates to state, district, and locality fields."""
    return await reverse_geocode(lat, lon)


@router.get("/forecasts")
async def live_forecasts(refresh: bool = False) -> dict:
    """Return latest prototype flood forecasts for configured sentinel zones."""
    if refresh:
        await live_data.poll()
    if not live_data.risk_scores:
        return {
            "available": False,
            "reason": "Live provider snapshot has not been initialized.",
            "status": live_data.status(),
            "forecasts": [],
        }
    return {
        "available": True,
        "status": live_data.status(),
        "forecasts": live_data.risk_scores,
    }


@router.get("/alerts")
async def translated_alerts(
    lang: str = "en",
    dispatch: bool = False,
    level: Literal["green", "orange", "red"] | None = None,
) -> dict:
    """Return translated live forecast alert payloads and optional mock dispatch logs."""
    target_language = lang if lang in SUPPORTED_LANGUAGES else "en"
    alerts = list(live_data.risk_scores)
    if level is not None:
        alerts = [alert for alert in alerts if alert["level"] == level]

    payloads = []
    for alert in alerts:
        checklist = registry.get("flood").get_safety_checklist() if registry.get("flood") else []
        translated_message = await translation_service.translate(
            alert["message"]
            if "message" in alert
            else "Flood risk is elevated near this sentinel.",
            target_language,
        )
        translated_checklist = await translation_service.translate_checklist(
            checklist, target_language
        )
        payload = {
            **alert,
            "message": translated_message["text"],
            "message_provider": translated_message["provider"],
            "checklist": translated_checklist,
        }
        if dispatch:
            payload["dispatch"] = await translation_service.dispatch(
                {
                    "message": alert.get("message", "Flood risk is elevated near this sentinel."),
                    "checklist": checklist,
                },
                target_language,
            )
        payloads.append(payload)

    return {
        "language": target_language,
        "available": bool(payloads),
        "dispatch_channel": "mock-sms-push" if dispatch else None,
        "alerts": payloads,
    }


@router.get("/sos")
async def list_sos_requests(
    incident_id: int | None = Query(default=None, ge=1),
    unassigned_only: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    """Return persisted SOS records, optionally limited to one incident."""
    try:
        statement = select(
            SOSRequest.id,
            SOSRequest.incident_id,
            SOSRequest.need_type,
            SOSRequest.description,
            SOSRequest.urgency,
            SOSRequest.status,
            SOSRequest.people_affected,
            SOSRequest.created_at,
            SOSRequest.updated_at,
            func.ST_Y(SOSRequest.location).label("latitude"),
            func.ST_X(SOSRequest.location).label("longitude"),
        )
        if incident_id is not None:
            statement = statement.where(SOSRequest.incident_id == incident_id)
        if unassigned_only:
            statement = statement.where(SOSRequest.incident_id.is_(None))
        rows = db.execute(statement.order_by(SOSRequest.created_at.desc())).mappings().all()
    except SQLAlchemyError as error:
        logger.exception("Could not retrieve SOS records")
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve SOS records from the database.",
        ) from error

    return {
        "available": True,
        "requests": [dict(row) for row in rows],
    }


@router.get("/shelters/nearest")
async def shelters_nearest(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> dict:
    """Return verified database shelters when available; otherwise label prototypes."""
    try:
        rows = (
            db.execute(
                select(
                    Shelter.id,
                    Shelter.name,
                    Shelter.capacity,
                    Shelter.current_occupancy,
                    Shelter.source_name,
                    func.ST_Y(Shelter.location).label("latitude"),
                    func.ST_X(Shelter.location).label("longitude"),
                )
                .where(Shelter.verification_status == "verified")
                .order_by(Shelter.id)
                .limit(limit)
            )
            .mappings()
            .all()
        )
    except SQLAlchemyError:
        rows = []

    verified = [
        {
            **dict(row),
            "distance_km": round(
                haversine_km(lat, lon, float(row["latitude"]), float(row["longitude"])),
                2,
            ),
            "verification_status": "verified",
        }
        for row in rows
    ]
    verified.sort(key=lambda item: item["distance_km"])

    if verified:
        return {
            "available": True,
            "source": "verified-postgis-catalogue",
            "verified": True,
            "shelters": verified,
        }

    prototype = nearest_shelters(lat, lon, limit)
    return {
        "available": False,
        "source": "prototype-pan-india-catalogue",
        "verified": False,
        "reason": "No verified shelter records are published in the database.",
        "shelters": prototype,
    }


@router.post("/route/evacuate")
async def evacuate(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    hazard: str | None = None,
    blocked_latitudes: list[float] = Query(default=[]),
    blocked_longitudes: list[float] = Query(default=[]),
) -> dict:
    """Compute a cached local fallback route with road-blockage penalties."""
    if len(blocked_latitudes) != len(blocked_longitudes):
        raise HTTPException(
            status_code=400,
            detail="blocked_latitudes and blocked_longitudes must have matching lengths",
        )
    blocked = list(zip(blocked_latitudes, blocked_longitudes))
    return evacuate_route(lat, lon, hazard=hazard, blocked=blocked)


@router.get("/local-readiness")
async def local_readiness(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    db: Session = Depends(get_db),
) -> dict:
    """Return coordinate-specific live feed and shelter readiness for the frontend."""
    nearby_scores = sorted(
        live_data.risk_scores,
        key=lambda score: haversine_km(
            lat,
            lon,
            float(score["latitude"]),
            float(score["longitude"]),
        ),
    )
    nearest_hazard = None
    if nearby_scores:
        nearest_hazard = dict(nearby_scores[0])
        nearest_hazard["distance_km"] = round(
            haversine_km(
                lat,
                lon,
                float(nearest_hazard["latitude"]),
                float(nearest_hazard["longitude"]),
            ),
            2,
        )

    try:
        verified_rows = (
            db.execute(
                select(
                    Shelter.id,
                    Shelter.name,
                    Shelter.capacity,
                    Shelter.current_occupancy,
                    Shelter.source_name,
                    func.ST_Y(Shelter.location).label("latitude"),
                    func.ST_X(Shelter.location).label("longitude"),
                ).where(Shelter.verification_status == "verified")
            )
            .mappings()
            .all()
        )
    except SQLAlchemyError:
        verified_rows = []

    verified_shelters = []
    for row in verified_rows:
        item = dict(row)
        item["distance_km"] = round(
            haversine_km(lat, lon, float(row["latitude"]), float(row["longitude"])),
            2,
        )
        verified_shelters.append(item)
    verified_shelters.sort(key=lambda item: item["distance_km"])

    return {
        "coordinates": {"latitude": lat, "longitude": lon},
        "live_hazard_feed": live_data.status(),
        "nearest_hazard_zone": nearest_hazard,
        "verified_shelters": verified_shelters[:5],
        "prototype_shelters": nearest_shelters(lat, lon, 3),
        "route_available": True,
    }


@router.get("/status")
async def service_status(db: Session = Depends(get_db)) -> dict:
    """Report actual initialization/connectivity for core prototype services."""
    live_status = live_data.status()
    try:
        verified_shelters = (
            db.scalar(
                select(func.count())
                .select_from(Shelter)
                .where(Shelter.verification_status == "verified")
            )
            or 0
        )
    except SQLAlchemyError:
        verified_shelters = 0
    return {
        "status": "degraded" if live_status["last_error"] else "ready",
        "telemetry": {
            "available": live_status["initialized"] and live_status["gdacs_reachable"],
            "last_update": live_status["last_update"],
            "last_error": live_status["last_error"],
            "sentinel_count": live_status["sentinel_count"],
        },
        "alerts": {
            "available": True,
            "count": len(live_data.risk_scores),
            "dispatch_channel": "mock-sms-push",
            "dispatch_log_count": len(translation_service.dispatch_log),
        },
        "shelters": {
            "available": bool(verified_shelters),
            "verification": "verified-postgis" if verified_shelters else "prototype-unverified",
            "verified_count": verified_shelters,
        },
        "routing": {
            "available": True,
            "mode": "OSMnx preferred; NetworkX local fallback",
            "osmnx_cache": True,
        },
        "translation": {
            "available": True,
            "bhashini": translation_service.bhashini_available(),
            "fallback": "google-translator-then-local-cache",
            "supported_languages": sorted(SUPPORTED_LANGUAGES),
        },
    }
