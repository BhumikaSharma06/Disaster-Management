"""Fault-tolerant three-tier alert translation service."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings

SUPPORTED_LANGUAGES = {
    "en",
    "hi",
    "mai",
    "bn",
    "ta",
    "te",
    "mr",
    "gu",
    "kn",
    "ml",
    "or",
    "pa",
    "as",
    "ur",
}
CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


class TranslationService:
    """Bhashini -> zero-key Google fallback -> local/English translation cascade."""

    def __init__(self) -> None:
        self._cache = self._load_cache()
        self.dispatch_log: list[dict[str, Any]] = []

    def _load_cache(self) -> dict[str, dict[str, str]]:
        try:
            payload = json.loads((CONFIG_DIR / "translations.json").read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def bhashini_available(self) -> bool:
        return bool(
            settings.bhashini_user_id
            and settings.bhashini_ulca_api_key
            and settings.bhashini_pipeline_endpoints
        )

    async def translate(self, text: str, target_language: str) -> dict[str, str]:
        if target_language == "en" or target_language not in SUPPORTED_LANGUAGES:
            return {"text": text, "provider": "english", "target_language": "en"}

        # Tier 1: Bhashini is only reported as available when credentials and
        # pipeline endpoints exist. The approved ULCA request contract remains
        # provider-specific and no payload is fabricated here.
        if self.bhashini_available():
            try:
                return await self._bhashini_translate(text, target_language)
            except Exception:
                pass

        # Tier 2: deep-translator is loaded lazily so a missing optional
        # package cannot prevent the API from starting.
        try:
            from deep_translator import GoogleTranslator

            translated = await asyncio.to_thread(
                GoogleTranslator(
                    source="en", target=self._google_language(target_language)
                ).translate,
                text,
            )
            return {
                "text": translated,
                "provider": "google-translator",
                "target_language": target_language,
            }
        except Exception:
            pass

        # Tier 3: deterministic offline templates, then English.
        translated = self._cache.get(target_language, {}).get(text)
        if translated:
            return {
                "text": translated,
                "provider": "local-cache",
                "target_language": target_language,
            }
        return {"text": text, "provider": "english-fallback", "target_language": target_language}

    async def _bhashini_translate(self, text: str, target_language: str) -> dict[str, str]:
        # No approved Bhashini DHruva payload contract is present. Returning an
        # explicit failure keeps this tier from inventing a successful translation.
        raise RuntimeError("Bhashini ULCA/Dhruva request contract is not configured")

    def _google_language(self, language: str) -> str:
        aliases = {"mai": "mai", "or": "or"}
        return aliases.get(language, language)

    async def dispatch(self, alert: dict[str, Any], language: str) -> dict[str, Any]:
        translated = await self.translate(alert.get("message", ""), language)
        checklist = await self.translate_checklist(alert.get("checklist", []), language)
        record = {
            "channel": "mock-sms-push",
            "language": language,
            "provider": translated["provider"],
            "message": translated["text"],
            "checklist": checklist,
            "delivery_status": "dispatched",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.dispatch_log.append(record)
        return record

    async def translate_checklist(self, items: list[str], language: str) -> list[str]:
        translated = []
        for item in items:
            result = await self.translate(item, language)
            translated.append(result["text"])
        return translated


translation_service = TranslationService()
