"""Environment-based application configuration."""

import json
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Configuration values supplied by the process environment."""

    basin_name: str
    database_url: str
    bhashini_user_id: str | None
    bhashini_ulca_api_key: str | None
    bhashini_pipeline_endpoints: dict[str, str]

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings and validate the optional Bhashini endpoint mapping."""
        raw_endpoints = os.getenv("BHASHINI_PIPELINE_ENDPOINTS", "{}")
        try:
            endpoints = json.loads(raw_endpoints)
        except json.JSONDecodeError as error:
            raise ValueError("BHASHINI_PIPELINE_ENDPOINTS must be a JSON object") from error
        if not isinstance(endpoints, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in endpoints.items()
        ):
            raise ValueError("BHASHINI_PIPELINE_ENDPOINTS must map strings to strings")

        return cls(
            basin_name=os.getenv("BASIN_NAME", "Lower Kosi Sub-Basin"),
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+psycopg://aapdasetu:change-me-for-local-development"
                "@localhost:5432/aapdasetu",
            ),
            bhashini_user_id=os.getenv("BHASHINI_USER_ID") or None,
            bhashini_ulca_api_key=os.getenv("BHASHINI_ULCA_API_KEY") or None,
            bhashini_pipeline_endpoints=endpoints,
        )


settings = Settings.from_env()
