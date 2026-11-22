"""Central registry for hazard modules."""

from app.hazards.base import HazardModule
from app.hazards.extensions import (
    CycloneModule,
    DroughtModule,
    HeatwaveModule,
    LandslideModule,
)
from app.hazards.flood import FloodModule


class HazardRegistry:
    """Register and resolve hazard modules without coupling core services."""

    def __init__(self) -> None:
        self._modules: dict[str, HazardModule] = {}

    def register(self, module: HazardModule) -> None:
        self._modules[module.hazard_type] = module

    def get(self, hazard_type: str) -> HazardModule | None:
        return self._modules.get(hazard_type)

    def all(self) -> dict[str, HazardModule]:
        return dict(self._modules)


registry = HazardRegistry()
registry.register(FloodModule())
registry.register(CycloneModule())
registry.register(LandslideModule())
registry.register(DroughtModule())
registry.register(HeatwaveModule())
