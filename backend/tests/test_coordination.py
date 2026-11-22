"""Tests for persistent request, supply, and responder coordination behavior."""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from app.api.auth import require_responder_or_admin
from app.api.coordination import (
    assign_supply_offer,
    cancel_help_request,
    cancel_supply_offer,
    coordination_summary,
    create_help_request,
    create_supply_offer,
    list_help_requests,
    list_my_help_requests,
    list_my_supply_offers,
    list_open_request_items,
    moderate_help_request,
    update_supply_offer_status,
)
from app.models.help_request import HelpRequest, HelpRequestItem
from app.models.supply_offer import ResponderAssignment, SupplyOffer
from app.models.user import User
from app.schemas.coordination import (
    HelpRequestCreate,
    HelpRequestModeration,
    OfferCancellation,
    OfferStatusUpdate,
    SupplyOfferCreate,
)


class _Rows:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows


class _ScalarRows:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def unique(self) -> "_ScalarRows":
        return self

    def all(self) -> list[Any]:
        return self._rows


class _CoordinationSession:
    """Small in-memory session double that preserves commit boundaries."""

    def __init__(self) -> None:
        self.requests: list[HelpRequest] = []
        self.items: list[HelpRequestItem] = []
        self.offers: list[SupplyOffer] = []
        self.assignments: list[ResponderAssignment] = []
        self.pending: list[Any] = []
        self.next_id = 1
        self.commits = 0
        self.last_statement: Any = None

    def scalar(self, statement: Any) -> Any:
        entity = statement.column_descriptions[0]["entity"]
        params = statement.compile().params
        if entity is HelpRequest:
            submission_id = next(
                (value for value in params.values() if isinstance(value, uuid.UUID)), None
            )
            target_id = next((value for value in params.values() if isinstance(value, int)), None)
            return next(
                (
                    request
                    for request in self.requests
                    if (
                        request.client_submission_id == submission_id
                        if submission_id is not None
                        else request.id == target_id
                    )
                ),
                None,
            )
        if entity is HelpRequestItem:
            target_id = next((value for value in params.values() if isinstance(value, int)), None)
            return next((item for item in self.items if item.id == target_id), None)
        if entity is SupplyOffer:
            submission_id = next(
                (value for value in params.values() if isinstance(value, uuid.UUID)), None
            )
            if submission_id is not None:
                return next(
                    (offer for offer in self.offers if offer.client_submission_id == submission_id),
                    None,
                )
            target_id = next((value for value in params.values() if isinstance(value, int)), None)
            return next((offer for offer in self.offers if offer.id == target_id), None)
        return None

    def execute(self, statement: Any) -> _Rows:
        self.last_statement = statement
        rows = []
        for item in self.items:
            request = next(row for row in self.requests if row.id == item.help_request_id)
            if (
                request.status in {"open", "partially_fulfilled"}
                and request.moderation_reason is None
                and item.units_fulfilled < item.units_required
            ):
                rows.append((item, request))
        return _Rows(rows)

    def scalars(self, statement: Any) -> _ScalarRows:
        self.last_statement = statement
        entity = statement.column_descriptions[0]["entity"]
        if entity is HelpRequest:
            return _ScalarRows(self.requests)
        if entity is HelpRequestItem:
            if getattr(statement.column_descriptions[0]["expr"], "key", None) == "id":
                return _ScalarRows([item.id for item in self.items])
            return _ScalarRows(self.items)
        if entity is SupplyOffer:
            return _ScalarRows(self.offers)
        return _ScalarRows([])

    def get(self, entity: type, identity: Any) -> Any:
        if entity is HelpRequest:
            return next((request for request in self.requests if request.id == identity), None)
        return None

    def add(self, instance: Any) -> None:
        self.pending.append(instance)

    def commit(self) -> None:
        self.commits += 1
        now = datetime.now(UTC)
        for instance in self.pending:
            if isinstance(instance, HelpRequest):
                instance.id = self.next_id
                self.next_id += 1
                instance.created_at = now
                for item in instance.items:
                    item.id = self.next_id
                    self.next_id += 1
                    item.help_request = instance
                    item.help_request_id = instance.id
                    self.items.append(item)
                self.requests.append(instance)
            elif isinstance(instance, SupplyOffer):
                instance.id = self.next_id
                self.next_id += 1
                instance.created_at = now
                instance.help_request_item = next(
                    item for item in self.items if item.id == instance.help_request_item_id
                )
                self.offers.append(instance)
            elif isinstance(instance, ResponderAssignment):
                instance.id = self.next_id
                self.next_id += 1
                instance.assigned_at = now
                instance.supply_offer = next(
                    offer for offer in self.offers if offer.id == instance.supply_offer_id
                )
                instance.supply_offer.assignment = instance
                self.assignments.append(instance)
        self.pending.clear()

    def refresh(self, instance: Any) -> None:
        del instance

    def rollback(self) -> None:
        self.pending.clear()


def _request_payload(**overrides: Any) -> HelpRequestCreate:
    values = {
        "client_submission_id": uuid.uuid4(),
        "item_name": "Drinking Water",
        "urgency": "urgent",
        "units_required": 5,
        "unit_label": "packets",
        "state": "Example State",
        "district": "Example District",
        "locality": "Example Ward",
        "landmark": "Community Hall",
        "contact_name": "Requester",
        "contact_phone": "+911234567890",
        "latitude": 26.2,
        "longitude": 86.4,
    }
    values.update(overrides)
    return HelpRequestCreate(**values)


def _offer_payload(item_id: int, units: int, **overrides: Any) -> SupplyOfferCreate:
    return SupplyOfferCreate(
        client_submission_id=uuid.uuid4(),
        help_request_item_id=item_id,
        units_offered=units,
        donor_name="Donor",
        donor_phone="+919876543210",
        pickup_location="Supply collection point",
        **overrides,
    )


def test_create_help_request_persists_item_and_postgis_point() -> None:
    db = _CoordinationSession()
    result = create_help_request(_request_payload(), db, None)

    assert result["status"] == "open"
    assert result["items"] == [
        {
            "id": 2,
            "item_name": "Drinking Water",
            "units_required": 5,
            "units_fulfilled": 0,
            "units_remaining": 5,
            "unit_label": "packets",
        }
    ]
    assert db.requests[0].location.data == "POINT(86.4 26.2)"
    assert db.commits == 1


def test_create_help_request_allows_coordinates_without_address_fields() -> None:
    db = _CoordinationSession()
    request_payload = _request_payload(state=None, district=None, locality=None)

    result = create_help_request(request_payload, db, None)

    assert result["state"] is None
    assert result["district"] is None
    assert result["locality"] is None
    assert result["latitude"] == 26.2
    assert result["longitude"] == 86.4


def test_open_items_expose_remaining_quantity_and_exclude_closed_or_filled() -> None:
    db = _CoordinationSession()
    create_help_request(_request_payload(), db, None)
    item = db.items[0]
    item.units_fulfilled = 2
    db.requests[0].status = "partially_fulfilled"

    rows = list_open_request_items(db)

    assert len(rows) == 1
    assert rows[0]["units_required"] == 5
    assert rows[0]["units_remaining"] == 3
    assert "contact_name" not in rows[0]
    item.units_fulfilled = item.units_required
    assert list_open_request_items(db) == []


def test_supply_offer_reserves_units_transactionally_and_updates_request_status() -> None:
    db = _CoordinationSession()
    create_help_request(_request_payload(), db, None)
    item = db.items[0]
    request = db.requests[0]

    first = create_supply_offer(_offer_payload(item.id, 3), db, None)
    assert first["status"] == "pending_responder"
    assert item.units_fulfilled == 3
    assert request.status == "partially_fulfilled"

    second = create_supply_offer(_offer_payload(item.id, 2), db, None)
    assert second["units_offered"] == 2
    assert item.units_fulfilled == 5
    assert request.status == "fulfilled"


def test_offer_rejects_quantity_above_remaining_without_mutating_request() -> None:
    db = _CoordinationSession()
    create_help_request(_request_payload(), db, None)
    item = db.items[0]

    with pytest.raises(HTTPException) as error:
        create_supply_offer(_offer_payload(item.id, 6), db, None)

    assert error.value.status_code == 409
    assert item.units_fulfilled == 0
    assert db.offers == []


def test_responder_claim_and_status_transitions_record_timestamps() -> None:
    db = _CoordinationSession()
    create_help_request(_request_payload(), db, None)
    offer = create_supply_offer(_offer_payload(db.items[0].id, 1), db, None)
    responder = User(id=uuid.uuid4(), is_responder=True, is_admin=False)

    assigned = assign_supply_offer(offer["id"], db, responder)
    assert assigned["status"] == "responder_assigned"
    assert assigned["assignment_responder_id"] == responder.id

    contacted = update_supply_offer_status(
        offer["id"], OfferStatusUpdate(status="contacted"), db, responder
    )
    assert contacted["status"] == "contacted"
    assert contacted["contacted_at"] is not None
    picked_up = update_supply_offer_status(
        offer["id"],
        OfferStatusUpdate(status="picked_up", actual_units_picked_up=1),
        db,
        responder,
    )
    assert picked_up["picked_up_at"] is not None
    delivered = update_supply_offer_status(
        offer["id"], OfferStatusUpdate(status="delivered"), db, responder
    )
    assert delivered["delivered_at"] is not None


def test_responder_cannot_skip_status_transition() -> None:
    db = _CoordinationSession()
    create_help_request(_request_payload(), db, None)
    offer = create_supply_offer(_offer_payload(db.items[0].id, 1), db, None)
    responder = User(id=uuid.uuid4(), is_responder=True, is_admin=False)
    assign_supply_offer(offer["id"], db, responder)

    with pytest.raises(HTTPException) as error:
        update_supply_offer_status(
            offer["id"], OfferStatusUpdate(status="delivered"), db, responder
        )

    assert error.value.status_code == 409


def test_picked_up_quantity_adjusts_reserved_units_and_request_status() -> None:
    db = _CoordinationSession()
    create_help_request(_request_payload(), db, None)
    item = db.items[0]
    request = db.requests[0]
    offer = create_supply_offer(_offer_payload(item.id, 4), db, None)
    responder = User(id=uuid.uuid4(), is_responder=True, is_admin=False)
    assign_supply_offer(offer["id"], db, responder)
    update_supply_offer_status(offer["id"], OfferStatusUpdate(status="contacted"), db, responder)

    updated = update_supply_offer_status(
        offer["id"],
        OfferStatusUpdate(status="picked_up", actual_units_picked_up=2),
        db,
        responder,
    )

    assert updated["actual_units_picked_up"] == 2
    assert item.units_fulfilled == 2
    assert request.status == "partially_fulfilled"


def test_offer_cancellation_releases_units_and_reopens_request() -> None:
    db = _CoordinationSession()
    create_help_request(_request_payload(), db, None)
    item = db.items[0]
    request = db.requests[0]
    offer = create_supply_offer(_offer_payload(item.id, 5), db, None)
    responder = User(id=uuid.uuid4(), is_responder=True, is_admin=False)
    assign_supply_offer(offer["id"], db, responder)

    cancelled = cancel_supply_offer(
        offer["id"], OfferCancellation(reason="donor_unreachable"), db, responder
    )

    assert cancelled["status"] == "cancelled"
    assert cancelled["cancellation_reason"] == "donor_unreachable"
    assert item.units_fulfilled == 0
    assert request.status == "open"


def test_donor_can_cancel_own_offer_without_responder_assignment() -> None:
    db = _CoordinationSession()
    create_help_request(_request_payload(), db, None)
    item = db.items[0]
    request = db.requests[0]
    donor = User(id=uuid.uuid4(), is_responder=False, is_admin=False)
    offer = create_supply_offer(_offer_payload(item.id, 2), db, donor)

    cancelled = cancel_supply_offer(
        offer["id"], OfferCancellation(reason="donor_cancelled"), db, donor
    )

    assert cancelled["status"] == "cancelled"
    assert item.units_fulfilled == 0
    assert request.status == "open"


def test_request_owner_can_cancel_and_release_active_offer_reservations() -> None:
    db = _CoordinationSession()
    owner = User(id=uuid.uuid4(), is_responder=False, is_admin=False)
    request_record = create_help_request(_request_payload(), db, owner)
    donor = User(id=uuid.uuid4(), is_responder=False, is_admin=False)
    offer = create_supply_offer(_offer_payload(db.items[0].id, 3), db, donor)

    cancelled = cancel_help_request(request_record["id"], db, owner)

    assert cancelled["status"] == "cancelled"
    assert cancelled["closed_at"] is not None
    assert db.items[0].units_fulfilled == 0
    assert db.offers[0].status == "cancelled"
    assert db.offers[0].cancellation_reason == "requester_cancelled"
    assert offer["id"] == db.offers[0].id


def test_user_cannot_cancel_another_accounts_help_request() -> None:
    db = _CoordinationSession()
    owner = User(id=uuid.uuid4(), is_responder=False, is_admin=False)
    request_record = create_help_request(_request_payload(), db, owner)
    other_user = User(id=uuid.uuid4(), is_responder=False, is_admin=False)

    with pytest.raises(HTTPException) as error:
        cancel_help_request(request_record["id"], db, other_user)

    assert error.value.status_code == 403
    assert db.requests[0].status == "open"


def test_personal_history_queries_are_scoped_by_account_id() -> None:
    db = _CoordinationSession()
    owner = User(id=uuid.uuid4(), is_responder=False, is_admin=False)
    create_help_request(_request_payload(), db, owner)
    offer_owner = User(id=uuid.uuid4(), is_responder=False, is_admin=False)
    create_supply_offer(_offer_payload(db.items[0].id, 1), db, offer_owner)

    requests = list_my_help_requests(db, owner)
    request_sql = str(db.last_statement.compile(dialect=postgresql.dialect()))
    assert len(requests) == 1
    assert "help_requests.created_by_user_id" in request_sql
    assert owner.id in db.last_statement.compile().params.values()

    offers = list_my_supply_offers(db, offer_owner)
    offer_sql = str(db.last_statement.compile(dialect=postgresql.dialect()))
    assert len(offers) == 1
    assert "supply_offers.donor_user_id" in offer_sql
    assert offer_owner.id in db.last_statement.compile().params.values()


def test_responder_request_list_supports_active_filter_and_spatial_ordering() -> None:
    db = _CoordinationSession()
    responder = User(id=uuid.uuid4(), is_responder=True, is_admin=False)

    list_help_requests(db, responder, active_only=True, latitude=26.0, longitude=86.0)

    sql = str(db.last_statement.compile(dialect=postgresql.dialect()))
    assert "help_requests.status IN" in sql
    assert "ST_Distance" in sql
    assert "geography" in sql


def test_cancelled_request_is_hidden_from_donors_and_rejects_new_offers() -> None:
    db = _CoordinationSession()
    owner = User(id=uuid.uuid4(), is_responder=False, is_admin=False)
    request = create_help_request(_request_payload(), db, owner)
    cancel_help_request(request["id"], db, owner)

    assert list_open_request_items(db) == []
    with pytest.raises(HTTPException) as error:
        create_supply_offer(_offer_payload(db.items[0].id, 1), db, None)
    assert error.value.status_code == 409


def test_cancelling_picked_up_offer_releases_only_actual_quantity() -> None:
    db = _CoordinationSession()
    create_help_request(_request_payload(), db, None)
    item = db.items[0]
    request = db.requests[0]
    offer = create_supply_offer(_offer_payload(item.id, 4), db, None)
    responder = User(id=uuid.uuid4(), is_responder=True, is_admin=False)
    assign_supply_offer(offer["id"], db, responder)
    update_supply_offer_status(offer["id"], OfferStatusUpdate(status="contacted"), db, responder)
    update_supply_offer_status(
        offer["id"],
        OfferStatusUpdate(status="picked_up", actual_units_picked_up=2),
        db,
        responder,
    )

    cancel_supply_offer(offer["id"], OfferCancellation(reason="donor_cancelled"), db, responder)

    assert item.units_fulfilled == 0
    assert item.units_fulfilled >= 0
    assert request.status == "open"


def test_moderation_close_cancels_active_offers_and_releases_units() -> None:
    db = _CoordinationSession()
    create_help_request(_request_payload(), db, None)
    item = db.items[0]
    request = db.requests[0]
    offer = create_supply_offer(_offer_payload(item.id, 3), db, None)
    responder = User(id=uuid.uuid4(), is_responder=True, is_admin=False)

    closed = moderate_help_request(
        request.id,
        HelpRequestModeration(action="close", reason="spam"),
        db,
        responder,
    )

    assert closed["status"] == "closed"
    assert closed["moderation_reason"] == "spam"
    assert item.units_fulfilled == 0
    assert db.offers[0].status == "cancelled"
    assert offer["id"] == db.offers[0].id


def test_flagged_request_is_hidden_from_donors_and_rejects_new_offers() -> None:
    db = _CoordinationSession()
    create_help_request(_request_payload(), db, None)
    request = db.requests[0]
    responder = User(id=uuid.uuid4(), is_responder=True, is_admin=False)
    moderate_help_request(
        request.id,
        HelpRequestModeration(action="flag", reason="duplicate"),
        db,
        responder,
    )

    assert list_open_request_items(db) == []
    with pytest.raises(HTTPException) as error:
        create_supply_offer(_offer_payload(db.items[0].id, 1), db, None)
    assert error.value.status_code == 409


def test_unapproved_user_cannot_access_responder_guard() -> None:
    user = User(id=uuid.uuid4(), is_responder=False, is_admin=False)
    with pytest.raises(HTTPException) as error:
        require_responder_or_admin(user)
    assert error.value.status_code == 403


def test_open_items_query_uses_postgis_distance_when_coordinates_exist() -> None:
    db = _CoordinationSession()
    list_open_request_items(db, latitude=26.0, longitude=86.0)

    sql = str(db.last_statement.compile(dialect=postgresql.dialect()))
    assert sql.index("ORDER BY") < sql.index("ST_Distance") < sql.index("CASE")
    assert "geography" in sql


def test_spatial_lists_fall_back_to_urgency_and_creation_order() -> None:
    db = _CoordinationSession()
    list_open_request_items(db)
    open_items_sql = str(db.last_statement.compile(dialect=postgresql.dialect()))
    assert "ST_Distance" not in open_items_sql
    assert "CASE" in open_items_sql
    assert "help_requests.created_at" in open_items_sql

    responder = User(id=uuid.uuid4(), is_responder=True, is_admin=False)
    from app.api.coordination import list_supply_offers

    list_supply_offers(db, responder)
    inbox_sql = str(db.last_statement.compile(dialect=postgresql.dialect()))
    assert "ST_Distance" not in inbox_sql
    assert "CASE" in inbox_sql
    assert "supply_offers.created_at" in inbox_sql


def test_responder_inbox_query_uses_postgis_distance_when_coordinates_exist() -> None:
    db = _CoordinationSession()
    responder = User(id=uuid.uuid4(), is_responder=True, is_admin=False)
    from app.api.coordination import list_supply_offers

    list_supply_offers(db, responder, latitude=26.0, longitude=86.0)

    sql = str(db.last_statement.compile(dialect=postgresql.dialect()))
    assert "ST_Distance" in sql
    assert "coalesce" in sql.lower()


def test_eoc_summary_aggregates_coordination_records() -> None:
    db = _CoordinationSession()
    create_help_request(_request_payload(), db, None)
    offer = create_supply_offer(_offer_payload(db.items[0].id, 2), db, None)
    responder = User(id=uuid.uuid4(), is_responder=True, is_admin=False)
    assign_supply_offer(offer["id"], db, responder)

    summary = coordination_summary(db, responder)

    assert summary["metrics"]["help_requests"] == 1
    assert summary["metrics"]["units_requested"] == 5
    assert summary["metrics"]["units_fulfilled"] == 2
    assert summary["metrics"]["responder_assignments"] == 1
    assert summary["supply_offers"][0]["status"] == "responder_assigned"
