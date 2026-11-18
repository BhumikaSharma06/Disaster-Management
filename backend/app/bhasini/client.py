"""Bhashini translation client placeholder."""

from app.core.config import Settings


class BhasiniClient:
    """Configuration-aware entry point for future Bhashini NMT requests."""

    def __init__(self, config: Settings) -> None:
        self._config = config

    async def translate(
        self, text: str, source_language: str, target_language: str
    ) -> str:
        """Translate text after the approved Bhashini contract is configured.

        Endpoint names, request payloads, and response formats are intentionally
        not assumed. Configure credentials and pipeline endpoints in the
        environment before implementing the HTTP request.
        """
        del text, source_language, target_language
        if not self._config.bhashini_user_id or not self._config.bhashini_ulca_api_key:
            raise RuntimeError("Bhashini user ID and ULCA API key must be configured")
        if not self._config.bhashini_pipeline_endpoints:
            raise RuntimeError("Bhashini pipeline endpoints must be configured")
        raise NotImplementedError("Bhashini request/response integration is not implemented yet")
