"""Safety-tip request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SafetyTipInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=160)
    content: str = Field(min_length=10, max_length=5000)
    hazard_type: str = Field(min_length=2, max_length=64)
    phase: str
    language: str = Field(default="en", min_length=2, max_length=16)
    region: str | None = Field(default=None, max_length=160)
    status: str = "draft"
    source: str | None = Field(default=None, max_length=254)

    @field_validator("title", "content", "hazard_type", "language", "region", "source")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("phase")
    @classmethod
    def validate_phase(cls, value: str) -> str:
        if value not in {"before", "during", "after"}:
            raise ValueError("Phase must be before, during, or after.")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"draft", "published", "archived"}:
            raise ValueError("Status must be draft, published, or archived.")
        return value


class SafetyTipResponse(SafetyTipInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
