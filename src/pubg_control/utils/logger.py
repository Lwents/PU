"""Enterprise logging configuration supporting file, console, and Tkinter UI streams."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
from typing import Callable, Optional

# Default log directory in project root
LOG_DIR = Path(__file__).resolve().parents[3] / "logs"
DEFAULT_LOG_FILE = LOG_DIR / "pubg_control.log"


class TkinterLogHandler(logging.Handler):
    """Log handler that redirects log messages safely to a Tkinter event callback."""

    def __init__(self, callback: Callable[[str], None]):
        super().__init__()
        self.callback = callback
        self.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.callback(msg)
        except Exception:
            self.handleError(record)


def setup_logger(
    name: str = "pubg_control",
    log_level: int = logging.INFO,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """Configures and returns the root application logger."""
    app_logger = logging.getLogger(name)
    app_logger.setLevel(log_level)

    if not app_logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        app_logger.addHandler(console_handler)

        # Rotating file handler
        target_file = log_file or DEFAULT_LOG_FILE
        try:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                target_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            app_logger.addHandler(file_handler)
        except OSError as exc:
            console_handler.emit(
                logging.LogRecord(
                    name, logging.WARNING, __file__, 57, f"Cannot write to log file: {exc}", (), None
                )
            )

    return app_logger
