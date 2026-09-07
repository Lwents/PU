"""Backwards-compatibility entrypoint for PUBG Control suite."""
from pathlib import Path
import sys

# Ensure src/ is on sys.path
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from main import main
from pubg_control.ui.app import PUBGControlApp

# Legacy alias
PUBGAutoToolGUI = PUBGControlApp

if __name__ == "__main__":
    main()
