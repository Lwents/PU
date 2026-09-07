"""Domain models for LDPlayer and emulator instances."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Instance:
    """Represents a single LDPlayer emulator instance."""
    index: int
    name: str
    hwnd: int
    ready: bool

    @property
    def label(self) -> str:
        """Formatted label used for comboboxes and UI display."""
        return f"{self.index} · {self.name}"
