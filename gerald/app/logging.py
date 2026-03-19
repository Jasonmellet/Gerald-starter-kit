from __future__ import annotations

import logging
from logging import Logger
from typing import Optional

from .config import get_settings


_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_root_logger(level: Optional[str] = None) -> None:
    """
    Configure the root logger for the Gerald application.

    Safe to call multiple times; subsequent calls are no-ops once configured.
    """

    if logging.getLogger().handlers:
        # Already configured
        return

    settings = get_settings()
    log_level = (level or settings.log_level).upper()

    handler = logging.StreamHandler()
    formatter = logging.Formatter(_LOG_FORMAT)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.addHandler(handler)


def get_logger(name: str) -> Logger:
    """
    Return a configured logger instance for the given module or component.
    """

    configure_root_logger()
    return logging.getLogger(name)


