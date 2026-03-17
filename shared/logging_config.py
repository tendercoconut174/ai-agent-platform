"""Centralized logging configuration with file + console output.

All log output includes timestamps (YYYY-MM-DD HH:MM:SS.mmm) for observability.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

_configured = False

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "platform.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
# Timestamp required: %(asctime)s.%(msecs)03d = YYYY-MM-DD HH:MM:SS.mmm
LOG_FORMAT = "%(asctime)s.%(msecs)03d | %(levelname)-7s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_LOG_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5


def setup_logging() -> None:
    """Configure root logger with timestamped console + rotating file handler.

    Safe to call multiple times; only configures once.
    """
    global _configured
    if _configured:
        return
    _configured = True

    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=MAX_LOG_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # Reduce noise from third-party libraries
    for noisy in (
        "httpx", "httpcore", "openai", "urllib3", "sqlalchemy.engine",
        "h2", "hpack", "primp", "cookie_store", "ddgs",
        "langsmith", "langchain", "langgraph",
        "rustls", "hyper_util", "hyper", "tower",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)
