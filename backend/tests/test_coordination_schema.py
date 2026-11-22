"""Verify coordination schema, migrations, and routes match the persistent workflow."""

from pathlib import Path

from app.api.auth import require_responder_or_admin
from app.api.coordination import router as coordination_router
from app.main import app
from app.models.help_request import HelpRequest, HelpRequestItem
from app.models.supply_offer import ResponderAssignment, SupplyOffer

MIGRATIONS = Path(__file__).parents[1] / "migrations" / "versions"


def _gist_index_names(model: type) -> set[str]:
    return {
        index.name
        for index in model.__table__.indexes
        if index.dialect_options["postgresql"].get("using") == "gist"
    }


def test_coordination_models_have_spatial_indexes_idempotency_and_foreign_keys() -> None:
    request_point = HelpRequest.__table__.c.location.type
    pickup_point = SupplyOffer.__table__.c.pickup_point.type
    assert (request_point.geometry_type, request_point.srid) == ("POINT", 4326)
    assert (pickup_point.geometry_type, pickup_point.srid) == ("POINT", 4326)
    assert _gist_index_names(HelpRequest) == {"idx_help_requests_location"}
    assert _gist_index_names(SupplyOffer) == {"idx_supply_offers_pickup_point"}

    assert HelpRequest.__table__.c.client_submission_id.unique is True
    assert SupplyOffer.__table__.c.client_submission_id.unique is True
    assert next(iter(HelpRequestItem.__table__.c.help_request_id.foreign_keys)).target_fullname == (
        "help_requests.id"
    )
    assert (
        next(iter(SupplyOffer.__table__.c.help_request_item_id.foreign_keys)).target_fullname
        == "help_request_items.id"
    )
    assert next(
        iter(ResponderAssignment.__table__.c.responder_id.foreign_keys)
    ).target_fullname == ("users.id")


def test_migrations_and_registered_routes_cover_coordination_schema() -> None:
    initial = (MIGRATIONS / "0008_supply_coordination.py").read_text(encoding="utf-8")
    hardening = (MIGRATIONS / "0009_coordination_hardening.py").read_text(encoding="utf-8")
    optional_address = (MIGRATIONS / "0011_optional_help_request_address.py").read_text(
        encoding="utf-8"
    )
    history = (MIGRATIONS / "0012_coordination_history.py").read_text(encoding="utf-8")
    assert 'postgresql_using="gist"' in initial
    assert "client_submission_id" in initial
    assert 'geometry_type="POINT", srid=4326' in initial
    assert "idx_supply_offers_pickup_point" in hardening
    assert "actual_units_picked_up" in hardening
    assert "cancelled" in hardening
    assert "coordination_rate_limits" in hardening
    assert "nullable=True" in optional_address
    assert "created_by_user_id" in history
    assert "donor_user_id" in history
    assert "cancelled" in history
    assert HelpRequest.__table__.c.created_by_user_id.nullable
    assert SupplyOffer.__table__.c.donor_user_id.nullable
    assert HelpRequest.__table__.c.state.nullable
    assert HelpRequest.__table__.c.district.nullable
    assert HelpRequest.__table__.c.locality.nullable

    paths = set(app.openapi()["paths"])
    assert {
        "/api/v1/help-requests",
        "/api/v1/help-requests/{request_id}/cancel",
        "/api/v1/help-requests/open-items",
        "/api/v1/help-requests/{request_id}/moderation",
        "/api/v1/coordination/my-help-requests",
        "/api/v1/coordination/my-supply-offers",
        "/api/v1/supply-offers",
        "/api/v1/supply-offers/{offer_id}/cancel",
        "/api/v1/supply-offers/{offer_id}/status",
    }.issubset(paths)

    moderation_route = next(
        route
        for route in coordination_router.routes
        if route.path == "/api/v1/help-requests/{request_id}/moderation"
    )
    assert any(
        dependency.call is require_responder_or_admin
        for dependency in moderation_route.dependant.dependencies
    )
    help_submission = next(
        route for route in coordination_router.routes if route.path == "/api/v1/help-requests"
    )
    assert any(
        dependency.call.__name__ == "throttle"
        for dependency in help_submission.dependant.dependencies
    )
