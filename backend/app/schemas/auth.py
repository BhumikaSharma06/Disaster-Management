"""Authentication request and response schemas."""

import re
import uuid
from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class RegistrationRequest(BaseModel):
    """User-provided account details."""

    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=160)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    is_responder: bool = False
    responder_unit: str | None = Field(default=None, max_length=160)
    responder_phone: str | None = Field(default=None, max_length=40)

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Trim surrounding whitespace and reject empty names."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Full name cannot be blank")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Normalize email addresses before storage and lookup."""
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid email address")
        return normalized

    @field_validator("responder_unit", "responder_phone")
    @classmethod
    def normalize_responder_field(cls, value: str | None) -> str | None:
        """Store optional responder details as null when left blank."""
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def validate_responder_details(self) -> "RegistrationRequest":
        """Prevent responder metadata for accounts not marked as responders."""
        if not self.is_responder and (self.responder_unit or self.responder_phone):
            raise ValueError("Responder details require is_responder=true")
        return self


class EmailRequest(BaseModel):
    """An email address used to request verification delivery."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Normalize email addresses before lookup."""
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid email address")
        return normalized


class VerifyEmailRequest(BaseModel):
    """One-time verification token payload."""

    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=20, max_length=200)


class LoginRequest(BaseModel):
    """Username/email and password credentials."""

    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(
        min_length=3,
        max_length=254,
        validation_alias=AliasChoices("identifier", "email"),
    )
    password: str = Field(min_length=1, max_length=128)

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        """Normalize a username or email address before lookup."""
        normalized = value.strip().lower()
        if not normalized or any(character.isspace() for character in normalized):
            raise ValueError("Enter a valid username or email address")
        return normalized


class UserResponse(BaseModel):
    """Public fields returned for an authenticated user."""

    id: uuid.UUID
    full_name: str
    email: str
    username: str | None = None
    is_responder: bool
    is_admin: bool
    is_super_admin: bool = False
    is_email_verified: bool
    responder_request_status: str

    model_config = ConfigDict(from_attributes=True)


class AccountProfileResponse(UserResponse):
    """Profile fields visible to the authenticated account owner."""

    contact_phone: str | None = None
    home_state: str | None = None
    home_district: str | None = None
    home_locality: str | None = None
    home_landmark: str | None = None


class ProfileUpdateRequest(BaseModel):
    """Optional contact and saved-address fields for the current user's profile."""

    model_config = ConfigDict(extra="forbid")

    contact_phone: str | None = Field(default=None, max_length=40)
    home_state: str | None = Field(default=None, max_length=120)
    home_district: str | None = Field(default=None, max_length=120)
    home_locality: str | None = Field(default=None, max_length=200)
    home_landmark: str | None = Field(default=None, max_length=200)

    @field_validator(
        "contact_phone",
        "home_state",
        "home_district",
        "home_locality",
        "home_landmark",
    )
    @classmethod
    def normalize_optional_profile_field(cls, value: str | None) -> str | None:
        """Trim supplied profile details and treat whitespace-only values as empty."""
        return value.strip() or None if value is not None else None

    @field_validator("contact_phone")
    @classmethod
    def validate_contact_phone(cls, value: str | None) -> str | None:
        """Reject a nonempty contact number that contains no digits."""
        if value is not None and not any(character.isdigit() for character in value):
            raise ValueError("Enter a valid contact phone number.")
        return value


class LoginResponse(BaseModel):
    """Bearer token and authenticated account payload."""

    access_token: str
    token_type: str = "bearer"
    user: AccountProfileResponse


class RegistrationResponse(BaseModel):
    """Safe registration status without disclosing the verification token."""

    message: str
    email: str
    verification_required: bool = True
    mailpit_ui_url: str | None = None


class VerificationResponse(BaseModel):
    """Email verification status."""

    message: str
    is_email_verified: bool


class ResponderProfileResponse(UserResponse):
    """Responder account information available to verified responders."""

    responder_unit: str | None
    responder_phone: str | None


class ResponderApprovalRequest(BaseModel):
    """Admin decision for a pending responder application."""

    decision: str

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: str) -> str:
        """Limit decisions to the supported approval outcomes."""
        if value not in {"approve", "reject"}:
            raise ValueError("Decision must be 'approve' or 'reject'")
        return value


class AdminRoleUpdateRequest(BaseModel):
    """Super Admin decision for normal-account Administrator promotion."""

    model_config = ConfigDict(extra="forbid")

    decision: str

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: str) -> str:
        if value not in {"promote", "demote"}:
            raise ValueError("Decision must be 'promote' or 'demote'")
        return value


class AdminUserResponse(UserResponse):
    """User fields available in the admin account directory."""

    responder_request_status: str
    responder_unit: str | None
    responder_phone: str | None
    created_at: datetime
    deleted_at: datetime | None = None
