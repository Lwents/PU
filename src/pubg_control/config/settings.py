"""Configuration settings management with validation and persistence."""
from dataclasses import asdict, dataclass
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default config path at project root
DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parents[3] / "settings.json"


@dataclass
class AppSettings:
    console: str = ""
    index: int = 0
    version: str = "Tự nhận diện"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppSettings":
        if not isinstance(data, dict):
            return cls()
        return cls(
            console=str(data.get("console", "")).strip(),
            index=int(data.get("index", 0)) if str(data.get("index", "")).isdigit() else 0,
            version=str(data.get("version", "Tự nhận diện")).strip(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SettingsManager:
    """Thread-safe settings loader and saver."""

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or DEFAULT_SETTINGS_PATH
        self._settings = self.load()

    @property
    def current(self) -> AppSettings:
        return self._settings

    def load(self) -> AppSettings:
        if not self.file_path.is_file():
            logger.debug("Settings file %s not found. Using defaults.", self.file_path)
            return AppSettings()
        try:
            content = self.file_path.read_text(encoding="utf-8")
            data = json.loads(content)
            logger.debug("Loaded settings successfully from %s", self.file_path)
            return AppSettings.from_dict(data)
        except (OSError, ValueError) as exc:
            logger.warning("Failed to parse settings from %s: %s. Using defaults.", self.file_path, exc)
            return AppSettings()

    def save(self, console: Optional[str] = None, index: Optional[int] = None, version: Optional[str] = None) -> bool:
        if console is not None:
            self._settings.console = console
        if index is not None:
            self._settings.index = index
        if version is not None:
            self._settings.version = version

        try:
            payload = json.dumps(self._settings.to_dict(), ensure_ascii=False, indent=2)
            self.file_path.write_text(payload, encoding="utf-8")
            logger.debug("Persisted settings to %s", self.file_path)
            return True
        except OSError as exc:
            logger.error("Error writing settings to %s: %s", self.file_path, exc)
            return False
