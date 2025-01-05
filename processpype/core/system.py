"""System configuration utilities for ProcessPype.

This module provides system-level configuration utilities, primarily focused on
timezone management across different operating systems.
"""

import os
import sys
import time

from pytz import timezone

# Default timezone setting for the application
default_timezone = timezone("UTC").zone


def setup_timezone(tz: str | None = default_timezone) -> None:
    """Configure system timezone for the application.

    Sets up the system timezone using environment variables and system calls.
    Handles platform-specific differences between Unix-like systems and Windows.

    Args:
        tz: Timezone name (e.g., "UTC", "America/New_York"). Defaults to UTC.
            If None, timezone setup is skipped.

    Raises:
        ValueError: If the timezone is invalid
    """
    if tz is None:
        return

    try:
        # Validate timezone
        timezone(tz)
    except Exception as e:
        raise ValueError(f"Invalid timezone: {tz}") from e

    # Set timezone environment variable
    os.environ["TZ"] = tz

    # Apply timezone setting based on platform
    if sys.platform != "win32":
        time.tzset()  # Unix-like systems only
    else:
        print("Windows does not support timezone setting.")
