"""Custom exception hierarchy for PUBG Control domain operations."""

class PUBGControlError(Exception):
    """Base exception for all application errors."""
    pass


class LDPlayerNotFoundError(PUBGControlError):
    """Raised when LDPlayer console executable is not found."""
    pass


class LDPlayerCommandError(PUBGControlError):
    """Raised when an LDPlayer console command fails or exits with an error."""
    pass


class ADBConnectionError(PUBGControlError):
    """Raised when ADB fails to connect or verify the target emulator."""
    pass


class GameLaunchError(PUBGControlError):
    """Raised when launching PUBG Mobile fails or cannot be verified."""
    pass
