"""Flood hazard module placeholder for the Lower Kosi prototype."""

from typing import Any

from app.hazards.base import HazardModule


class FloodModule(HazardModule):
    """Flood-specific implementation point; modeling is not implemented yet."""

    hazard_type = "flood"

    def fit(self, training_data: Any) -> None:
        """Reserve the training interface for a future flood model."""
        raise NotImplementedError("Flood model training is not implemented yet")

    def predict_risk(self, observations: Any) -> Any:
        """Reserve the inference interface for a future flood model."""
        raise NotImplementedError("Flood risk prediction is not implemented yet")

    def evaluate(self, test_data: Any, expected: Any) -> dict[str, float]:
        """Reserve evaluation for a future flood model."""
        raise NotImplementedError("Flood model evaluation is not implemented yet")
