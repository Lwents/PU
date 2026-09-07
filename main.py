"""Standard enterprise application entrypoint for PUBG Control."""
import os
from pathlib import Path
import sys
import tkinter as tk

# Ensure 'src' is on Python sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pubg_control.ui.app import PUBGControlApp
from pubg_control.utils.logger import setup_logger


def main() -> None:
    """Initialize logging, construct the main window, and start event loop."""
    logger = setup_logger("pubg_control")
    logger.info("Starting PUBG Control Desktop Suite...")

    root = tk.Tk()
    app = PUBGControlApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user. Exiting.")
        app.on_closing()


if __name__ == "__main__":
    main()
