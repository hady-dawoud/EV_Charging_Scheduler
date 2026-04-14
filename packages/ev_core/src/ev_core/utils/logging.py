"""Small logging helpers for scripts, notebooks, and future pipelines."""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a module logger with a null handler for import safety."""

    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger
