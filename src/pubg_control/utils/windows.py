"""Windows OS-specific window management and focus helpers."""
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


def focus_window_by_hwnd(hwnd: int) -> bool:
    """Safely restore and activate a window given its Win32 HWND."""
    if not hwnd:
        logger.warning("Invalid window handle: %s", hwnd)
        return False

    try:
        import pygetwindow as gw

        window = gw.Win32Window(hwnd)
        if window.isMinimized:
            window.restore()
        window.activate()
        time.sleep(0.5)
        return True
    except Exception as exc:
        logger.error("Failed activating window HWND %d: %s", hwnd, exc)
        return False
