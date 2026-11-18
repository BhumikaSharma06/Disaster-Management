"""Interface for loading archived datasets without assuming source URLs."""

from typing import Any, Protocol


class DataLoader(Protocol):
    """Contract for a local or approved archived-data source adapter."""

    def load(self, dataset_name: str) -> Any:
        """Load a named dataset from a configured local source.

        TODO: Define supported dataset names and file formats after the archive
        sources have been selected; do not add guessed government URLs here.
        """
        ...
