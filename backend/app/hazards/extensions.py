"""Clean prototype modules for hazards beyond the working flood reference."""

from typing import Any

from app.hazards.base import HazardModule


class PrototypeHazardModule(HazardModule):
    hazard_type = "prototype"

    def compute_risk_score(self, observations: dict[str, Any]) -> float:
        return 0.0

    def generate_alert_payload(self, observations: dict[str, Any]) -> dict[str, Any]:
        return {
            "hazard_type": self.hazard_type,
            "level": "green",
            "score": 0.0,
            "message": f"Live {self.hazard_type} inference is not yet validated.",
            "observations": observations,
        }

    def fit(self, training_data: Any) -> None:
        return None

    def predict_risk(self, observations: Any) -> Any:
        return self.compute_risk_score(observations)

    def evaluate(self, test_data: Any, expected: Any) -> dict[str, float]:
        return {"not_evaluated": 0.0}


class CycloneModule(PrototypeHazardModule):
    hazard_type = "cyclone"


class LandslideModule(PrototypeHazardModule):
    hazard_type = "landslide"


class DroughtModule(PrototypeHazardModule):
    hazard_type = "drought"


class HeatwaveModule(PrototypeHazardModule):
    hazard_type = "heatwave"
