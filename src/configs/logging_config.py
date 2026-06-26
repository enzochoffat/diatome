"""
Centralised logging configuration for the FIBE project.
"""

from __future__ import annotations

import logging
import logging.config
from pathlib import Path


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "fibe.log"


def setup_logging(log_level: int = logging.INFO) -> None:
    """
    Configure the global logging system.

    Args:
        log_level: Default logging level (DEBUG, INFO, etc.).
    """
    LOG_DIR.mkdir(exist_ok=True)

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "standard": {
                "format": (
                    "%(asctime)s | %(levelname)-8s | "
                    "%(name)s | "
                    "%(message)s"
                )
            },
            "detailed": {
                "format": (
                    "%(asctime)s | %(levelname)-8s | "
                    "%(name)s | "
                    "%(filename)s:%(lineno)d | "
                    "%(message)s"
                )
            },
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },

            "file": {
                "class": "logging.FileHandler",
                "level": logging.DEBUG,
                "formatter": "detailed",
                "filename": str(LOG_FILE),
                "encoding": "utf-8",
            },
        },

        "root": {
            "level": log_level,
            "handlers": ["console", "file"],
        },
    }

    logging.config.dictConfig(logging_config)