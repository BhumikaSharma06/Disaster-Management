"""Common interface for hazard-specific model modules."""

from abc import ABC, abstractmethod
from typing import Any


class HazardModule(ABC):
    """Contract implemented by each hazard-specific model."""

    hazard_type: str

    @abstractmethod
    def fit(self, training_data: Any) -> None:
        """Train or initialize this module from prepared training data."""

    @abstractmethod
    def predict_risk(self, observations: Any) -> Any:
        """Return risk estimates for the supplied observations."""

    @abstractmethod
    def evaluate(self, test_data: Any, expected: Any) -> dict[str, float]:
        """Evaluate predictions and return named numeric metrics."""
