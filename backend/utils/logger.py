"""Logging configuration for AfriHealth Assistant backend."""

import logging
import sys
from backend.config import settings


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    return logger


def setup_logger(name: str = "afrihealth") -> logging.Logger:
    return get_logger(name)


def log_info(message: str, *args):
    get_logger("afrihealth").info(message, *args)


def log_error(message: str, *args):
    get_logger("afrihealth").error(message, *args)


def log_debug(message: str, *args):
    get_logger("afrihealth").debug(message, *args)
