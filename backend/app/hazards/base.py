"""Common interface for hazard-specific model modules."""

from abc import ABC, abstractmethod
from typing import Any


class HazardModule(ABC):
    """Contract implemented by each hazard-specific model."""

    hazard_type: str

    async def ingest_telemetry(self, observations: dict[str, Any]) -> dict[str, Any]:
        """Normalize provider telemetry before hazard-specific risk inference."""
        return observations

    def compute_risk_score(self, observations: dict[str, Any]) -> float:
        """Compute a bounded 0-100 prototype risk score."""
        return 0.0

    def generate_alert_payload(self, observations: dict[str, Any]) -> dict[str, Any]:
        """Generate a localized-safe English alert template payload."""
        return {
            "hazard_type": self.hazard_type,
            "level": "green",
            "message": "No verified live advisory has been generated.",
            "observations": observations,
        }

    def get_safety_checklist(self) -> list[str]:
        """Return the hazard-specific English checklist."""
        return ["Follow instructions from authorized local emergency services."]

    @abstractmethod
    def fit(self, training_data: Any) -> None:
        """Train or initialize this module from prepared training data."""

    @abstractmethod
    def predict_risk(self, observations: Any) -> Any:
        """Return risk estimates for the supplied observations."""

    @abstractmethod
    def evaluate(self, test_data: Any, expected: Any) -> dict[str, float]:
        """Evaluate predictions and return named numeric metrics."""
