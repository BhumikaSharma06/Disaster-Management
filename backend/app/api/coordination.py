"""Persistent help requests, supply offers, and responder workflow APIs."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from geoalchemy2 import Geography, WKTElement
from sqlalchemy import case, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.auth import get_current_user, get_optional_current_user, require_responder_or_admin
from app.core.database import get_db
from app.models.help_request import HelpRequest, HelpRequestItem
from app.models.supply_offer import ResponderAssignment, SupplyOffer
from app.models.user import User
from app.schemas.coordination import (
    HelpRequestCreate,
    HelpRequestModeration,
    HelpRequestResponse,
    OfferCancellation,
    OfferStatusUpdate,
    OpenRequestItemResponse,
    SupplyOfferCreate,
    SupplyOfferResponse,
)
from app.services.coordination_rate_limit import enforce_submission_limit

router = APIRouter(prefix="/api/v1", tags=["help and supply coordination"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CoordinationUser = Annotated[User, Depends(require_responder_or_admin)]
AccountUser = Annotated[User, Depends(get_current_user)]


def _item_record(item: HelpRequestItem) -> dict:
    """Serialize a quantity-tracked request item."""
    return {
        "id": item.id,
        "item_name": item.item_name,
        "units_required": item.units_required,
        "units_fulfilled": item.units_fulfilled,
        "units_remaining": item.units_required - item.units_fulfilled,
        "unit_label": item.unit_label,
    }


def _request_record(request: HelpRequest) -> dict:
    """Serialize a request with contacts and nested fulfillment totals."""
    return {
        "id": request.id,
        "urgency": request.urgency,
        "state": request.state,
        "district": request.district,
        "locality": request.locality,
        "landmark": request.landmark,
        "contact_name": request.contact_name,
        "contact_phone": request.contact_phone,
        "notes": request.notes,
        "latitude": request.latitude,
        "longitude": request.longitude,
        "status": request.status,
        "moderation_reason": request.moderation_reason,
        "moderated_at": request.moderated_at,
        "closed_at": request.closed_at,
        "created_at": request.created_at,
        "items": [_item_record(item) for item in request.items],
    }


def _offer_record(offer: SupplyOffer) -> dict:
    """Serialize an offer and the contact/location details responders need."""
    item = offer.help_request_item
    request = item.help_request
    assignment = offer.assignment
    return {
        "id": offer.id,
        "help_request_item_id": item.id,
        "item_name": item.item_name,
        "units_offered": offer.units_offered,
        "actual_units_picked_up": offer.actual_units_picked_up,
        "unit_label": item.unit_label,
        "donor_name": offer.donor_name,
        "donor_phone": offer.donor_phone,
        "pickup_location": offer.pickup_location,
        "pickup_latitude": offer.pickup_latitude,
        "pickup_longitude": offer.pickup_longitude,
        "notes": offer.notes,
        "status": offer.status,
        "contacted_at": offer.contacted_at,
        "picked_up_at": offer.picked_up_at,
        "delivered_at": offer.delivered_at,
        "cancelled_at": offer.cancelled_at,
        "cancellation_reason": offer.cancellation_reason,
        "created_at": offer.created_at,
        "requester_name": request.contact_name,
        "requester_phone": request.contact_phone,
        "drop_location": ", ".join(
            part
            for part in (request.landmark, request.locality, request.district, request.state)
            if part
        ),
        "assignment_responder_id": assignment.responder_id if assignment else None,
        "assigned_at": assignment.assigned_at if assignment else None,
    }


def _submission_throttle(endpoint: str):
    """Create a route dependency for cross-process public submission throttling."""

    def throttle(request: Request, db: DatabaseSession) -> None:
        enforce_submission_limit(request, db, endpoint)

    return throttle


def _urgency_order():
    return case(
        (HelpRequest.urgency == "urgent", 0),
        (HelpRequest.urgency == "high", 1),
        else_=2,
    )


def _recalculate_request_status(request: HelpRequest) -> None:
    """Recompute parent status from item quantities without reopening closed requests."""
    if request.status in {"closed", "cancelled"}:
        return
    if all(item.units_fulfilled >= item.units_required for item in request.items):
        request.status = "fulfilled"
    elif any(item.units_fulfilled > 0 for item in request.items):
        request.status = "partially_fulfilled"
    else:
        request.status = "open"


def _reserved_offer_units(offer: SupplyOffer) -> int:
    """Return the quantity currently reserved by an offer."""
    if offer.status == "picked_up" and offer.actual_units_picked_up is not None:
        return offer.actual_units_picked_up
    return offer.units_offered


def _cancel_offer(offer: SupplyOffer, item: HelpRequestItem, user: User, reason: str) -> None:
    """Release an active offer's reservation and persist its cancellation."""
    item.units_fulfilled = max(0, item.units_fulfilled - _reserved_offer_units(offer))
    offer.status = "cancelled"
    offer.cancelled_at = datetime.now(UTC)
    offer.cancellation_reason = reason
    offer.cancelled_by_user_id = user.id


def _offer_query():
    return select(SupplyOffer).options(
        joinedload(SupplyOffer.help_request_item).joinedload(HelpRequestItem.help_request),
        joinedload(SupplyOffer.assignment),
    )


@router.post(
    "/help-requests",
    response_model=HelpRequestResponse,
    status_code=201,
    dependencies=[Depends(_submission_throttle("help-requests"))],
)
def create_help_request(
    payload: HelpRequestCreate,
    db: DatabaseSession,
    user: User | None = Depends(get_optional_current_user),
) -> dict:
    """Persist a geocoded request and its first quantity-tracked item."""
    existing = db.scalar(
        select(HelpRequest)
        .where(HelpRequest.client_submission_id == payload.client_submission_id)
        .options(selectinload(HelpRequest.items))
    )
    if existing is not None:
        return _request_record(existing)

    request = HelpRequest(
        client_submission_id=payload.client_submission_id,
        created_by_user_id=user.id if user else None,
        urgency=payload.urgency,
        state=payload.state,
        district=payload.district,
        locality=payload.locality,
        landmark=payload.landmark,
        contact_name=payload.contact_name,
        contact_phone=payload.contact_phone,
        notes=payload.notes,
        latitude=payload.latitude,
        longitude=payload.longitude,
        location=WKTElement(f"POINT({payload.longitude} {payload.latitude})", srid=4326),
        status="open",
        items=[
            HelpRequestItem(
                item_name=payload.item_name,
                units_required=payload.units_required,
                units_fulfilled=0,
                unit_label=payload.unit_label,
            )
        ],
    )
    db.add(request)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        existing = db.scalar(
            select(HelpRequest)
            .where(HelpRequest.client_submission_id == payload.client_submission_id)
            .options(selectinload(HelpRequest.items))
        )
        if existing is not None:
            return _request_record(existing)
        raise HTTPException(
            status_code=409, detail="The help request could not be saved."
        ) from error
    db.refresh(request)
    return _request_record(request)


@router.get("/help-requests", response_model=list[HelpRequestResponse])
def list_help_requests(
    db: DatabaseSession,
    _user: CoordinationUser,
    request_status: Literal["open", "partially_fulfilled", "fulfilled", "closed", "cancelled"]
    | None = Query(default=None, alias="status"),
    active_only: bool = False,
    item: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    location: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
) -> list[dict]:
    """List contact-bearing requests for response staff, optionally spatially sorted."""
    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=422, detail="Provide both latitude and longitude, or neither."
        )
    query = select(HelpRequest).options(selectinload(HelpRequest.items))
    if active_only:
        query = query.where(HelpRequest.status.in_(("open", "partially_fulfilled")))
    if request_status is not None:
        query = query.where(HelpRequest.status == request_status)
    if item:
        query = query.where(
            HelpRequest.items.any(
                func.lower(HelpRequestItem.item_name).contains(item.strip().lower())
            )
        )
    if location:
        pattern = f"%{location.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(HelpRequest.locality).like(pattern),
                func.lower(HelpRequest.district).like(pattern),
                func.lower(HelpRequest.state).like(pattern),
                func.lower(HelpRequest.landmark).like(pattern),
            )
        )
    if latitude is not None and longitude is not None:
        point = WKTElement(f"POINT({longitude} {latitude})", srid=4326)
        query = query.order_by(
            func.ST_Distance(
                cast(HelpRequest.location, Geography(srid=4326)),
                cast(point, Geography(srid=4326)),
            ),
            _urgency_order(),
            HelpRequest.created_at,
        )
    else:
        query = query.order_by(_urgency_order(), HelpRequest.created_at)
    return [_request_record(row) for row in db.scalars(query).all()]


@router.get("/coordination/my-help-requests", response_model=list[HelpRequestResponse])
def list_my_help_requests(db: DatabaseSession, user: AccountUser) -> list[dict]:
    """Return only help requests owned by the authenticated account."""
    requests = db.scalars(
        select(HelpRequest)
        .where(HelpRequest.created_by_user_id == user.id)
        .options(selectinload(HelpRequest.items))
        .order_by(HelpRequest.created_at.desc())
    ).all()
    return [_request_record(request) for request in requests]


@router.get("/help-requests/open-items", response_model=list[OpenRequestItemResponse])
def list_open_request_items(
    db: DatabaseSession,
    item: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    location: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
) -> list[dict]:
    """List safe-to-share request items that still need supplies."""
    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=422, detail="Provide both latitude and longitude, or neither."
        )
    query = (
        select(HelpRequestItem, HelpRequest)
        .join(HelpRequest, HelpRequest.id == HelpRequestItem.help_request_id)
        .where(
            HelpRequest.status.in_(("open", "partially_fulfilled")),
            HelpRequest.moderation_reason.is_(None),
            HelpRequestItem.units_fulfilled < HelpRequestItem.units_required,
        )
    )
    if item:
        query = query.where(func.lower(HelpRequestItem.item_name).contains(item.strip().lower()))
    if location:
        pattern = f"%{location.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(HelpRequest.locality).like(pattern),
                func.lower(HelpRequest.district).like(pattern),
                func.lower(HelpRequest.state).like(pattern),
                func.lower(HelpRequest.landmark).like(pattern),
            )
        )
    if latitude is not None and longitude is not None:
        point = WKTElement(f"POINT({longitude} {latitude})", srid=4326)
        distance = func.ST_Distance(
            cast(HelpRequest.location, Geography(srid=4326)),
            cast(point, Geography(srid=4326)),
        )
        query = query.order_by(
            distance, _urgency_order(), HelpRequest.created_at, HelpRequestItem.id
        )
    else:
        query = query.order_by(_urgency_order(), HelpRequest.created_at, HelpRequestItem.id)
    rows = db.execute(query).all()
    return [
        {
            **_item_record(item_row),
            "help_request_id": request_row.id,
            "urgency": request_row.urgency,
            "state": request_row.state,
            "district": request_row.district,
            "locality": request_row.locality,
            "landmark": request_row.landmark,
            "latitude": request_row.latitude,
            "longitude": request_row.longitude,
        }
        for item_row, request_row in rows
    ]


@router.post(
    "/supply-offers",
    response_model=SupplyOfferResponse,
    status_code=201,
    dependencies=[Depends(_submission_throttle("supply-offers"))],
)
def create_supply_offer(
    payload: SupplyOfferCreate,
    db: DatabaseSession,
    user: User | None = Depends(get_optional_current_user),
) -> dict:
    """Atomically reserve remaining units and record the donor offer."""
    existing = db.scalar(
        _offer_query().where(SupplyOffer.client_submission_id == payload.client_submission_id)
    )
    if existing is not None:
        return _offer_record(existing)

    item = db.scalar(
        select(HelpRequestItem)
        .where(HelpRequestItem.id == payload.help_request_item_id)
        .with_for_update()
    )
    if item is None:
        raise HTTPException(
            status_code=404, detail="The selected help request is no longer available."
        )
    request = db.scalar(
        select(HelpRequest)
        .where(HelpRequest.id == item.help_request_id)
        .with_for_update()
        .options(selectinload(HelpRequest.items))
    )
    if (
        request is None
        or request.status not in {"open", "partially_fulfilled"}
        or request.moderation_reason is not None
    ):
        raise HTTPException(status_code=409, detail="The selected help request is closed.")

    remaining = item.units_required - item.units_fulfilled
    if payload.units_offered > remaining:
        raise HTTPException(
            status_code=409,
            detail=f"Only {remaining} {item.unit_label} remain for this request.",
        )

    pickup_point = (
        WKTElement(
            f"POINT({payload.pickup_longitude} {payload.pickup_latitude})",
            srid=4326,
        )
        if payload.pickup_latitude is not None
        else None
    )
    offer = SupplyOffer(
        client_submission_id=payload.client_submission_id,
        help_request_item_id=item.id,
        donor_user_id=user.id if user else None,
        units_offered=payload.units_offered,
        donor_name=payload.donor_name,
        donor_phone=payload.donor_phone,
        pickup_location=payload.pickup_location,
        pickup_latitude=payload.pickup_latitude,
        pickup_longitude=payload.pickup_longitude,
        pickup_point=pickup_point,
        notes=payload.notes,
        status="pending_responder",
    )
    item.units_fulfilled += payload.units_offered
    _recalculate_request_status(request)
    db.add(offer)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        existing = db.scalar(
            _offer_query().where(SupplyOffer.client_submission_id == payload.client_submission_id)
        )
        if existing is not None:
            return _offer_record(existing)
        raise HTTPException(
            status_code=409, detail="The supply offer could not be saved."
        ) from error
    db.refresh(offer)
    return _offer_record(offer)


@router.get("/supply-offers", response_model=list[SupplyOfferResponse])
def list_supply_offers(
    db: DatabaseSession,
    _user: CoordinationUser,
    offer_status: Literal[
        "pending_responder",
        "responder_assigned",
        "contacted",
        "picked_up",
        "delivered",
        "cancelled",
    ]
    | None = Query(default=None, alias="status"),
    item: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    location: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
) -> list[dict]:
    """List offers with requester/donor contacts for verified responders."""
    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=422, detail="Provide both latitude and longitude, or neither."
        )
    query = _offer_query().join(SupplyOffer.help_request_item).join(HelpRequestItem.help_request)
    if offer_status is not None:
        query = query.where(SupplyOffer.status == offer_status)
    if item:
        query = query.where(func.lower(HelpRequestItem.item_name).contains(item.strip().lower()))
    if location:
        pattern = f"%{location.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(HelpRequest.locality).like(pattern),
                func.lower(HelpRequest.district).like(pattern),
                func.lower(HelpRequest.state).like(pattern),
                func.lower(HelpRequest.landmark).like(pattern),
                func.lower(SupplyOffer.pickup_location).like(pattern),
            )
        )
    if latitude is not None and longitude is not None:
        point = WKTElement(f"POINT({longitude} {latitude})", srid=4326)
        distance = func.ST_Distance(
            cast(
                func.coalesce(SupplyOffer.pickup_point, HelpRequest.location),
                Geography(srid=4326),
            ),
            cast(point, Geography(srid=4326)),
        )
        order = (distance, _urgency_order(), SupplyOffer.created_at)
    else:
        order = (_urgency_order(), SupplyOffer.created_at)
    offers = db.scalars(query.order_by(*order)).unique().all()
    return [_offer_record(offer) for offer in offers]


@router.get("/coordination/my-supply-offers", response_model=list[SupplyOfferResponse])
def list_my_supply_offers(db: DatabaseSession, user: AccountUser) -> list[dict]:
    """Return only supply offers owned by the authenticated account."""
    offers = (
        db.scalars(
            _offer_query()
            .where(SupplyOffer.donor_user_id == user.id)
            .order_by(SupplyOffer.created_at.desc())
        )
        .unique()
        .all()
    )
    return [_offer_record(offer) for offer in offers]


@router.post("/supply-offers/{offer_id}/cancel", response_model=SupplyOfferResponse)
def cancel_supply_offer(
    offer_id: int,
    payload: OfferCancellation,
    db: DatabaseSession,
    user: AccountUser,
) -> dict:
    """Allow its donor, assigned responder, or an admin to cancel an active offer."""
    existing_offer = db.scalar(select(SupplyOffer).where(SupplyOffer.id == offer_id))
    if existing_offer is None:
        raise HTTPException(status_code=404, detail="Supply offer not found.")
    item_id = existing_offer.help_request_item_id
    item = db.scalar(select(HelpRequestItem).where(HelpRequestItem.id == item_id).with_for_update())
    offer = db.scalar(select(SupplyOffer).where(SupplyOffer.id == offer_id).with_for_update())
    if item is None or offer is None:
        raise HTTPException(status_code=404, detail="Supply offer not found.")
    if offer.status in {"cancelled", "delivered"}:
        raise HTTPException(status_code=409, detail="This offer can no longer be cancelled.")
    is_assigned_responder = (
        offer.assignment is not None and offer.assignment.responder_id == user.id
    )
    if not user.is_admin and offer.donor_user_id != user.id and not is_assigned_responder:
        raise HTTPException(
            status_code=403,
            detail="Only the donor, assigned responder, or an administrator can cancel.",
        )
    request = db.scalar(
        select(HelpRequest)
        .where(HelpRequest.id == item.help_request_id)
        .with_for_update()
        .options(selectinload(HelpRequest.items))
    )
    if request is None:
        raise HTTPException(status_code=404, detail="Help request not found.")

    _cancel_offer(offer, item, user, payload.reason)
    _recalculate_request_status(request)
    db.commit()
    db.refresh(offer)
    return _offer_record(offer)


@router.post("/help-requests/{request_id}/cancel", response_model=HelpRequestResponse)
def cancel_help_request(
    request_id: int,
    db: DatabaseSession,
    user: AccountUser,
) -> dict:
    """Cancel an owned active request and release all undelivered offer reservations."""
    item_ids = list(
        db.scalars(
            select(HelpRequestItem.id)
            .where(HelpRequestItem.help_request_id == request_id)
            .order_by(HelpRequestItem.id)
        ).all()
    )
    items = (
        list(
            db.scalars(
                select(HelpRequestItem)
                .where(HelpRequestItem.id.in_(item_ids))
                .order_by(HelpRequestItem.id)
                .with_for_update()
            ).all()
        )
        if item_ids
        else []
    )
    request = db.scalar(
        select(HelpRequest)
        .where(HelpRequest.id == request_id)
        .with_for_update()
        .options(selectinload(HelpRequest.items))
    )
    if request is None:
        raise HTTPException(status_code=404, detail="Help request not found.")
    if request.created_by_user_id != user.id:
        raise HTTPException(status_code=403, detail="You can only cancel your own help requests.")
    if request.status not in {"open", "partially_fulfilled"}:
        raise HTTPException(
            status_code=409, detail="Only active, unfulfilled help requests can be cancelled."
        )

    item_by_id = {item.id: item for item in items}
    offers = (
        db.scalars(
            select(SupplyOffer)
            .where(
                SupplyOffer.help_request_item_id.in_(item_ids),
                SupplyOffer.status.notin_(("cancelled", "delivered")),
            )
            .order_by(SupplyOffer.id)
            .with_for_update()
        ).all()
        if item_ids
        else []
    )
    for offer in offers:
        if offer.help_request_item_id in item_by_id and offer.status not in {
            "cancelled",
            "delivered",
        }:
            _cancel_offer(
                offer,
                item_by_id[offer.help_request_item_id],
                user,
                "requester_cancelled",
            )
    request.status = "cancelled"
    request.closed_at = datetime.now(UTC)
    request.closed_by_user_id = user.id
    db.commit()
    db.refresh(request)
    return _request_record(request)


@router.post("/help-requests/{request_id}/moderation", response_model=HelpRequestResponse)
def moderate_help_request(
    request_id: int,
    payload: HelpRequestModeration,
    db: DatabaseSession,
    user: CoordinationUser,
) -> dict:
    """Flag a request or close it while releasing every undelivered reservation."""
    item_ids = list(
        db.scalars(
            select(HelpRequestItem.id)
            .where(HelpRequestItem.help_request_id == request_id)
            .order_by(HelpRequestItem.id)
        ).all()
    )
    items = (
        list(
            db.scalars(
                select(HelpRequestItem)
                .where(HelpRequestItem.id.in_(item_ids))
                .order_by(HelpRequestItem.id)
                .with_for_update()
            ).all()
        )
        if item_ids
        else []
    )
    request = db.scalar(
        select(HelpRequest)
        .where(HelpRequest.id == request_id)
        .with_for_update()
        .options(selectinload(HelpRequest.items))
    )
    if request is None:
        raise HTTPException(status_code=404, detail="Help request not found.")
    if request.status in {"closed", "cancelled"}:
        raise HTTPException(status_code=409, detail="This help request is no longer active.")

    changed_at = datetime.now(UTC)
    request.moderation_reason = payload.reason
    request.moderated_by_user_id = user.id
    request.moderated_at = changed_at
    if payload.action == "close":
        request.status = "closed"
        request.closed_by_user_id = user.id
        request.closed_at = changed_at
        item_by_id = {item.id: item for item in items}
        offers = (
            db.scalars(
                select(SupplyOffer)
                .where(
                    SupplyOffer.help_request_item_id.in_(item_ids),
                    SupplyOffer.status.notin_(("cancelled", "delivered")),
                )
                .order_by(SupplyOffer.id)
                .with_for_update()
            ).all()
            if item_ids
            else []
        )
        for offer in offers:
            _cancel_offer(
                offer,
                item_by_id[offer.help_request_item_id],
                user,
                "request_closed",
            )
    db.commit()
    db.refresh(request)
    return _request_record(request)


@router.get("/coordination/inbox-count")
def responder_inbox_count(db: DatabaseSession, _user: CoordinationUser) -> dict[str, int]:
    """Count active requests and offers for the shared responder navigation badge."""
    request_count = db.scalar(
        select(func.count(HelpRequest.id)).where(
            HelpRequest.status.in_(("open", "partially_fulfilled"))
        )
    )
    offer_count = db.scalar(
        select(func.count(SupplyOffer.id)).where(
            SupplyOffer.status.notin_(("delivered", "cancelled"))
        )
    )
    return {"count": int(request_count or 0) + int(offer_count or 0)}


@router.post("/supply-offers/{offer_id}/assign", response_model=SupplyOfferResponse)
def assign_supply_offer(
    offer_id: int,
    db: DatabaseSession,
    user: CoordinationUser,
) -> dict:
    """Claim an unassigned offer for the authenticated responder."""
    offer = db.scalar(select(SupplyOffer).where(SupplyOffer.id == offer_id).with_for_update())
    if offer is None:
        raise HTTPException(status_code=404, detail="Supply offer not found.")
    if offer.assignment is not None:
        if offer.assignment.responder_id == user.id:
            return _offer_record(offer)
        raise HTTPException(status_code=409, detail="This offer has already been claimed.")
    if offer.status != "pending_responder":
        raise HTTPException(status_code=409, detail="This offer is no longer available to claim.")

    assignment = ResponderAssignment(supply_offer_id=offer.id, responder_id=user.id)
    offer.assignment = assignment
    offer.status = "responder_assigned"
    db.add(assignment)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Another responder has claimed this offer."
        ) from error
    db.refresh(offer)
    return _offer_record(offer)


@router.patch("/supply-offers/{offer_id}/status", response_model=SupplyOfferResponse)
def update_supply_offer_status(
    offer_id: int,
    payload: OfferStatusUpdate,
    db: DatabaseSession,
    user: CoordinationUser,
) -> dict:
    """Advance an assigned offer through contact, pickup, and delivery."""
    existing_offer = db.scalar(select(SupplyOffer).where(SupplyOffer.id == offer_id))
    if existing_offer is None:
        raise HTTPException(status_code=404, detail="Supply offer not found.")
    item_id = existing_offer.help_request_item_id
    item = db.scalar(select(HelpRequestItem).where(HelpRequestItem.id == item_id).with_for_update())
    offer = db.scalar(select(SupplyOffer).where(SupplyOffer.id == offer_id).with_for_update())
    if offer is None or item is None:
        raise HTTPException(status_code=404, detail="Supply offer not found.")
    assignment = offer.assignment
    if assignment is None or (assignment.responder_id != user.id and not user.is_admin):
        raise HTTPException(
            status_code=403, detail="Only the assigned responder can update this offer."
        )
    request = db.scalar(
        select(HelpRequest)
        .where(HelpRequest.id == item.help_request_id)
        .with_for_update()
        .options(selectinload(HelpRequest.items))
    )
    if request is None:
        raise HTTPException(status_code=404, detail="Help request not found.")
    if request.status in {"closed", "cancelled"} or request.moderation_reason is not None:
        raise HTTPException(status_code=409, detail="This help request is not active.")
    next_status = {
        "responder_assigned": "contacted",
        "contacted": "picked_up",
        "picked_up": "delivered",
    }.get(offer.status)
    if payload.status != next_status:
        raise HTTPException(
            status_code=409,
            detail=(
                "Offer status must progress from assigned to contacted, picked up, then delivered."
            ),
        )

    changed_at = datetime.now(UTC)
    offer.status = payload.status
    if payload.status == "contacted":
        offer.contacted_at = changed_at
    elif payload.status == "picked_up":
        if payload.actual_units_picked_up is None:
            raise HTTPException(status_code=422, detail="Confirm the actual quantity picked up.")
        offer.picked_up_at = changed_at
        item.units_fulfilled = max(
            0,
            min(
                item.units_required,
                item.units_fulfilled + payload.actual_units_picked_up - offer.units_offered,
            ),
        )
        offer.actual_units_picked_up = payload.actual_units_picked_up
    else:
        offer.delivered_at = changed_at
    _recalculate_request_status(request)
    db.commit()
    db.refresh(offer)
    return _offer_record(offer)


@router.get("/coordination/summary")
def coordination_summary(db: DatabaseSession, _user: CoordinationUser) -> dict:
    """Return live coordination metrics and records for the EOC dashboard."""
    requests = db.scalars(
        select(HelpRequest)
        .options(selectinload(HelpRequest.items))
        .order_by(HelpRequest.created_at.desc())
    ).all()
    offers = db.scalars(_offer_query().order_by(SupplyOffer.created_at.desc())).unique().all()
    records = [_offer_record(offer) for offer in offers]
    return {
        "metrics": {
            "help_requests": len(requests),
            "open_help_requests": sum(request.status == "open" for request in requests),
            "partially_fulfilled_requests": sum(
                request.status == "partially_fulfilled" for request in requests
            ),
            "fulfilled_requests": sum(request.status == "fulfilled" for request in requests),
            "cancelled_help_requests": sum(request.status == "cancelled" for request in requests),
            "supply_offers": len(offers),
            "pending_responder": sum(offer.status == "pending_responder" for offer in offers),
            "responder_assigned": sum(offer.status == "responder_assigned" for offer in offers),
            "delivered": sum(offer.status == "delivered" for offer in offers),
            "cancelled": sum(offer.status == "cancelled" for offer in offers),
            "units_requested": sum(
                item.units_required for request in requests for item in request.items
            ),
            "units_fulfilled": sum(
                item.units_fulfilled for request in requests for item in request.items
            ),
            "responder_assignments": sum(offer.assignment is not None for offer in offers),
        },
        "help_requests": [_request_record(request) for request in requests],
        "supply_offers": records,
    }
