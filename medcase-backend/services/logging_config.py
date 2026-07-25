# services/logging_config.py
"""
App-wide logging setup: replaces the scattered print() calls across
main.py/routers/agents. Console output (all levels) plus three separate
level-specific files under medcase-backend/logs/ (info.log, warning.log,
error.log) — split by level rather than one combined file, so latency/token
INFO noise doesn't bury real WARNING/ERROR events when skimming logs during
a thesis demo or while debugging a failed evaluation run.

Call configure_logging() once at process startup (main.py does this at
import time); every module then just does `logging.getLogger(__name__)`.
"""
import logging
import os

LOGS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
)

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"

_configured = False


class _MaxLevelFilter(logging.Filter):
    """Lets a handler capture ONLY up to (and including) a given level, so
    e.g. info.log doesn't also fill up with every WARNING/ERROR."""

    def __init__(self, max_level: int):
        super().__init__()
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self.max_level


def configure_logging(level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return
    _configured = True

    os.makedirs(LOGS_DIR, exist_ok=True)
    formatter = logging.Formatter(_LOG_FORMAT)

    root = logging.getLogger()
    root.setLevel(level)

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    info_handler = logging.FileHandler(os.path.join(LOGS_DIR, "info.log"), encoding="utf-8")
    info_handler.setLevel(logging.INFO)
    info_handler.addFilter(_MaxLevelFilter(logging.INFO))
    info_handler.setFormatter(formatter)
    root.addHandler(info_handler)

    warning_handler = logging.FileHandler(os.path.join(LOGS_DIR, "warning.log"), encoding="utf-8")
    warning_handler.setLevel(logging.WARNING)
    warning_handler.addFilter(_MaxLevelFilter(logging.WARNING))
    warning_handler.setFormatter(formatter)
    root.addHandler(warning_handler)

    error_handler = logging.FileHandler(os.path.join(LOGS_DIR, "error.log"), encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root.addHandler(error_handler)
