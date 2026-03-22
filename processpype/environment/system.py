"""System-level environment setup for ProcessPype.

Handles timezone configuration, project directory resolution, and run ID generation.
"""

import hashlib
import logging
import os
import sys
import time
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from processpype.config.models import AppConfig

logger = logging.getLogger("processpype.environment")


def setup_timezone(tz: str = "UTC") -> None:
    """Configure the system timezone.

    Args:
        tz: IANA timezone name (e.g. "UTC", "America/New_York").

    Raises:
        ValueError: If the timezone name is not recognized.
    """
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, KeyError) as e:
        raise ValueError(f"Invalid timezone: {tz}") from e

    os.environ["TZ"] = tz
    if sys.platform != "win32":
        time.tzset()


def generate_run_id() -> str:
    """Generate a short, unique run ID based on the current timestamp."""
    now = datetime.now(tz=UTC).isoformat()
    return hashlib.sha256(now.encode()).hexdigest()[:12]


def get_project_dir() -> str:
    """Return the project root directory.

    Reads from the ``PROJECT_DIR`` environment variable, falling back to cwd.
    """
    return os.environ.get("PROJECT_DIR", os.getcwd())


def setup_environment(config: AppConfig) -> None:
    """Run all environment setup steps.

    Args:
        config: Application configuration containing timezone and other settings.
    """
    setup_timezone(config.timezone)

    # Publish runtime tokens as env vars for downstream use (e.g. log file paths)
    os.environ.setdefault("PROJECT_DIR", get_project_dir())
    os.environ.setdefault("RUN_ID", generate_run_id())
    os.environ.setdefault("APP_NAME", config.title)
    os.environ.setdefault("DEPLOY_ENV", config.environment)

    logger.debug(
        "Environment ready: tz=%s project_dir=%s",
        config.timezone,
        os.environ["PROJECT_DIR"],
    )
