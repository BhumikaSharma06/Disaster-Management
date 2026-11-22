"""Flood hazard module placeholder for the Lower Kosi prototype."""

from typing import Any

from app.hazards.base import HazardModule


class FloodModule(HazardModule):
    """Flood-specific implementation point; modeling is not implemented yet."""

    hazard_type = "flood"

    async def ingest_telemetry(self, observations: dict[str, Any]) -> dict[str, Any]:
        return observations

    def compute_risk_score(self, observations: dict[str, Any]) -> float:
        precipitation = float(observations.get("precipitation", 0.0) or 0.0)
        discharge = float(observations.get("river_discharge", 0.0) or 0.0)
        soil = float(observations.get("soil_moisture", 0.0) or 0.0)
        elevation = float(observations.get("elevation", 100.0) or 100.0)
        score = min(
            100.0,
            precipitation * 0.8
            + soil * 25.0
            + discharge * 0.02
            + max(0.0, 150.0 - elevation) * 0.03,
        )
        return round(score, 2)

    def generate_alert_payload(self, observations: dict[str, Any]) -> dict[str, Any]:
        score = self.compute_risk_score(observations)
        level = "red" if score >= 75 else "orange" if score >= 45 else "green"
        return {
            "hazard_type": "flood",
            "level": level,
            "score": score,
            "message": "Flood risk is elevated near this sentinel."
            if level != "green"
            else "No elevated flood risk detected in this prototype sample.",
            "observations": observations,
        }

    def get_safety_checklist(self) -> list[str]:
        return [
            "Move to higher ground and avoid walking or driving through flood water.",
            "Unplug electrical equipment and avoid touching flooded power sources.",
            "Carry essential medicines, drinking water, documents, and charged phones.",
            "Follow instructions from authorized local emergency services.",
        ]

    def fit(self, training_data: Any) -> None:
        """Reserve the training interface for a future flood model."""
        raise NotImplementedError("Flood model training is not implemented yet")

    def predict_risk(self, observations: Any) -> Any:
        """Reserve the inference interface for a future flood model."""
        raise NotImplementedError("Flood risk prediction is not implemented yet")

    def evaluate(self, test_data: Any, expected: Any) -> dict[str, float]:
        """Reserve evaluation for a future flood model."""
        raise NotImplementedError("Flood model evaluation is not implemented yet")
