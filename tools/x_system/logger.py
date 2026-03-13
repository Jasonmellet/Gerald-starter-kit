from __future__ import annotations

import logging
from pathlib import Path


def build_logger(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("x_system")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(stream_handler)
    return logger

