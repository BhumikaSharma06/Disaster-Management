"""Environment-based application configuration."""

import json
import os
from dataclasses import dataclass

from sqlalchemy.engine import URL


@dataclass(frozen=True)
class Settings:
    """Configuration values supplied by the process environment."""

    basin_name: str
    database_url: str
    bhashini_user_id: str | None
    bhashini_ulca_api_key: str | None
    bhashini_pipeline_endpoints: dict[str, str]
    telemetry_sentinels_path: str
    google_maps_api_key: str | None
    smtp_host: str
    smtp_port: int
    smtp_from_email: str
    mailpit_ui_url: str | None
    frontend_base_url: str
    auth_jwt_secret: str
    auth_access_token_minutes: int
    email_verification_token_minutes: int

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings and validate the optional Bhashini endpoint mapping."""
        raw_endpoints = os.getenv("BHASHINI_PIPELINE_ENDPOINTS", "{}")
        try:
            endpoints = json.loads(raw_endpoints)
        except json.JSONDecodeError as error:
            raise ValueError("BHASHINI_PIPELINE_ENDPOINTS must be a JSON object") from error
        if not isinstance(endpoints, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in endpoints.items()
        ):
            raise ValueError("BHASHINI_PIPELINE_ENDPOINTS must map strings to strings")

        return cls(
            basin_name=os.getenv("BASIN_NAME", "Lower Kosi Sub-Basin"),
            database_url=os.getenv("DATABASE_URL")
            or URL.create(
                drivername="postgresql+psycopg",
                username=os.getenv("POSTGRES_USER", "aapdasetu"),
                password=os.getenv("POSTGRES_PASSWORD", "change-me-for-local-development"),
                host=os.getenv("DATABASE_HOST", "localhost"),
                port=int(os.getenv("DATABASE_PORT", "5433")),
                database=os.getenv("POSTGRES_DB", "aapdasetu"),
            ).render_as_string(hide_password=False),
            bhashini_user_id=os.getenv("BHASHINI_USER_ID") or None,
            bhashini_ulca_api_key=os.getenv("BHASHINI_ULCA_API_KEY") or None,
            bhashini_pipeline_endpoints=endpoints,
            telemetry_sentinels_path=os.getenv("TELEMETRY_SENTINELS_PATH", ""),
            google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY") or None,
            smtp_host=os.getenv("SMTP_HOST", "localhost"),
            smtp_port=int(os.getenv("SMTP_PORT", "1025")),
            smtp_from_email=os.getenv("SMTP_FROM_EMAIL", "noreply@aapdasetu.local"),
            mailpit_ui_url=os.getenv("MAILPIT_UI_URL") or None,
            frontend_base_url=os.getenv("FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/"),
            auth_jwt_secret=os.getenv("AUTH_JWT_SECRET", ""),
            auth_access_token_minutes=int(os.getenv("AUTH_ACCESS_TOKEN_MINUTES", "60")),
            email_verification_token_minutes=int(
                os.getenv("EMAIL_VERIFICATION_TOKEN_MINUTES", "1440")
            ),
        )


settings = Settings.from_env()
