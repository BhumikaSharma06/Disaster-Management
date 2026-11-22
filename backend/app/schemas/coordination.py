"""Validated API contracts for help requests and supply coordination."""

import math
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CleanText = Annotated[str, Field(min_length=1)]


def _trim(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("This field must not be blank.")
    return normalized


class HelpRequestCreate(BaseModel):
    """A request for one kind of aid at a geocoded location."""

    model_config = ConfigDict(extra="forbid")

    client_submission_id: uuid.UUID
    item_name: Annotated[str, Field(min_length=1, max_length=120)]
    urgency: Literal["urgent", "high", "general"]
    units_required: Annotated[int, Field(ge=1, le=1_000_000)] = 1
    unit_label: Annotated[str, Field(min_length=1, max_length=40)] = "units"
    state: Annotated[str | None, Field(max_length=120)] = None
    district: Annotated[str | None, Field(max_length=120)] = None
    locality: Annotated[str | None, Field(max_length=200)] = None
    landmark: Annotated[str | None, Field(max_length=200)] = None
    contact_name: Annotated[str, Field(min_length=1, max_length=160)]
    contact_phone: Annotated[str, Field(min_length=5, max_length=40)]
    notes: Annotated[str | None, Field(max_length=4000)] = None
    latitude: Annotated[float, Field(ge=-90, le=90)]
    longitude: Annotated[float, Field(ge=-180, le=180)]

    @field_validator("item_name", "unit_label", "contact_name")
    @classmethod
    def trim_required(cls, value: str) -> str:
        return _trim(value)

    @field_validator("state", "district", "locality", "landmark", "notes")
    @classmethod
    def trim_optional(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("contact_phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        normalized = _trim(value)
        if not any(character.isdigit() for character in normalized):
            raise ValueError("Enter a valid contact phone number.")
        return normalized

    @model_validator(mode="after")
    def validate_coordinates(self) -> "HelpRequestCreate":
        if not math.isfinite(self.latitude) or not math.isfinite(self.longitude):
            raise ValueError("Coordinates must be finite.")
        return self


class SupplyOfferCreate(BaseModel):
    """An offer to supply a quantity of an open request item."""

    model_config = ConfigDict(extra="forbid")

    client_submission_id: uuid.UUID
    help_request_item_id: Annotated[int, Field(gt=0)]
    units_offered: Annotated[int, Field(ge=1, le=1_000_000)]
    donor_name: Annotated[str, Field(min_length=1, max_length=160)]
    donor_phone: Annotated[str, Field(min_length=5, max_length=40)]
    pickup_location: Annotated[str, Field(min_length=1, max_length=300)]
    pickup_latitude: Annotated[float, Field(ge=-90, le=90)] | None = None
    pickup_longitude: Annotated[float, Field(ge=-180, le=180)] | None = None
    notes: Annotated[str | None, Field(max_length=4000)] = None

    @field_validator("donor_name", "pickup_location")
    @classmethod
    def trim_required(cls, value: str) -> str:
        return _trim(value)

    @field_validator("notes")
    @classmethod
    def trim_notes(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("donor_phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        normalized = _trim(value)
        if not any(character.isdigit() for character in normalized):
            raise ValueError("Enter a valid contact phone number.")
        return normalized

    @model_validator(mode="after")
    def validate_pickup_coordinates(self) -> "SupplyOfferCreate":
        if (self.pickup_latitude is None) != (self.pickup_longitude is None):
            raise ValueError("Provide both pickup coordinates or neither.")
        if self.pickup_latitude is not None and (
            not math.isfinite(self.pickup_latitude) or not math.isfinite(self.pickup_longitude)
        ):
            raise ValueError("Pickup coordinates must be finite.")
        return self


class OfferStatusUpdate(BaseModel):
    """A permitted responder progress transition."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["contacted", "picked_up", "delivered"]
    actual_units_picked_up: Annotated[int, Field(ge=0, le=1_000_000)] | None = None

    @model_validator(mode="after")
    def validate_actual_pickup(self) -> "OfferStatusUpdate":
        if self.status == "picked_up" and self.actual_units_picked_up is None:
            raise ValueError("Confirm the actual quantity picked up.")
        if self.status != "picked_up" and self.actual_units_picked_up is not None:
            raise ValueError("Actual pickup quantity is only valid when marking picked up.")
        return self


class OfferCancellation(BaseModel):
    """A responder-recorded reason for cancelling an offer."""

    model_config = ConfigDict(extra="forbid")

    reason: Literal["donor_cancelled", "donor_unreachable"]


class HelpRequestModeration(BaseModel):
    """A responder or administrator flag/close action for a request."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["flag", "close"]
    reason: Literal["spam", "duplicate"]


class RequestItemResponse(BaseModel):
    """One quantity-tracked item in a help request."""

    id: int
    item_name: str
    units_required: int
    units_fulfilled: int
    units_remaining: int
    unit_label: str


class HelpRequestResponse(BaseModel):
    """Public request details, including nested item fulfillment totals."""

    id: int
    urgency: str
    state: str | None
    district: str | None
    locality: str | None
    landmark: str | None
    contact_name: str
    contact_phone: str
    notes: str | None
    latitude: float
    longitude: float
    status: str
    moderation_reason: str | None
    moderated_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    items: list[RequestItemResponse]


class OpenRequestItemResponse(RequestItemResponse):
    """Safe request-item fields used by donors to choose an open need."""

    help_request_id: int
    urgency: str
    state: str | None
    district: str | None
    locality: str | None
    landmark: str | None
    latitude: float
    longitude: float


class SupplyOfferResponse(BaseModel):
    """An offer record with request and responder coordination details."""

    id: int
    help_request_item_id: int
    item_name: str
    units_offered: int
    actual_units_picked_up: int | None
    unit_label: str
    donor_name: str
    donor_phone: str
    pickup_location: str
    pickup_latitude: float | None
    pickup_longitude: float | None
    notes: str | None
    status: str
    contacted_at: datetime | None
    picked_up_at: datetime | None
    delivered_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    created_at: datetime
    requester_name: str
    requester_phone: str
    drop_location: str
    assignment_responder_id: uuid.UUID | None
    assigned_at: datetime | None
