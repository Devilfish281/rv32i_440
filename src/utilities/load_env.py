# utilities/load_env.py

import logging
import os
import re
from pathlib import Path
from typing import Optional

from dotenv import find_dotenv, load_dotenv

logger = logging.getLogger(__name__)


def env_true(name: str, default: bool = False) -> bool:
    """Return True if env var looks truthy: 1/true/yes/on (case-insensitive)."""
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _validate_register_dump(value: str) -> bool:
    """Validate REGISTER_DUMP value."""
    return bool(re.fullmatch(r"(?i)^(1|0|true|false|yes|no|on|off)$", value.strip()))


def is_register_dump_enabled() -> bool:
    """Check if REGISTER_DUMP environment variable is set to a truthy value."""
    return env_true("REGISTER_DUMP")


# LOG_LEVEL=re.DEBUG
def read_log_level() -> int:
    """Read LOG_LEVEL environment variable."""
    level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    return {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }.get(level, logging.INFO)


def load_environment() -> None:
    """
    Load environment variables from .env (if present) and validate required vars.
    Raises ValueError on missing/invalid critical variables.
    """
    logger.info("Loading environment variables.")

    # Locate a .env file in the project (if present) and load it without overriding existing env vars.
    env_path = find_dotenv()
    if env_path:
        load_dotenv(env_path, override=False)
        logger.debug("Loaded .env from %s", env_path)
    else:
        logger.debug(
            ".env file not found; continuing with existing environment variables"
        )

    register_dump = os.getenv("REGISTER_DUMP")
    if not _validate_register_dump(register_dump or ""):
        logger.error("REGISTER_DUMP is missing or invalid")
        raise ValueError("REGISTER_DUMP environment variable missing or invalid")
    logger.info("REGISTER_DUMP is set to %s", register_dump)
    logger.info("Environment variables loaded successfully.")
