"""Game UI coordinate profiles and resolutions."""
from dataclasses import dataclass, field
from typing import Dict, Tuple

from pubg_control.config.constants import DEFAULT_COORDINATES


@dataclass
class CoordinateProfile:
    """Represents click target coordinates on the screen for game actions."""
    name: str = "Default 1080p Profile"
    coordinates: Dict[str, Tuple[int, int]] = field(default_factory=lambda: dict(DEFAULT_COORDINATES))

    def get(self, key: str) -> Tuple[int, int]:
        """Retrieve coordinate tuple for a given action key."""
        if key not in self.coordinates:
            raise KeyError(f"Coordinate key '{key}' not configured in profile '{self.name}'.")
        return self.coordinates[key]
