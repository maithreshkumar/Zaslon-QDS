"""
Structured logging configuration for Zaslon-QDS.
Never logs sensitive credentials, tokens, or raw secrets.
"""
import logging
import sys
from .config import settings


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("zaslon")
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging()
