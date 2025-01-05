"""Unit tests for system utilities."""

import os
import sys
from unittest.mock import patch

import pytest

from processpype.core.system import default_timezone, setup_timezone


def test_default_timezone() -> None:
    """Test default timezone value."""
    assert default_timezone == "UTC"


@pytest.mark.skipif(sys.platform == "win32", reason="tzset not supported on Windows")
def test_setup_timezone_unix() -> None:
    """Test timezone setup on Unix-like systems."""
    test_tz = "America/New_York"

    with patch("time.tzset") as mock_tzset:
        setup_timezone(test_tz)

        assert os.environ["TZ"] == test_tz
        mock_tzset.assert_called_once()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_setup_timezone_windows() -> None:
    """Test timezone setup on Windows."""
    test_tz = "America/New_York"

    with patch("builtins.print") as mock_print:
        setup_timezone(test_tz)

        assert os.environ["TZ"] == test_tz
        mock_print.assert_called_once_with("Windows does not support timezone setting.")


def test_setup_timezone_none() -> None:
    """Test timezone setup with None value."""
    # Save original TZ value
    original_tz = os.environ.get("TZ")

    try:
        # Remove TZ from environment if it exists
        if "TZ" in os.environ:
            del os.environ["TZ"]

        setup_timezone(None)

        # Verify TZ wasn't set
        assert "TZ" not in os.environ

    finally:
        # Restore original TZ value if it existed
        if original_tz is not None:
            os.environ["TZ"] = original_tz
        elif "TZ" in os.environ:
            del os.environ["TZ"]


def test_setup_timezone_error() -> None:
    """Test setup timezone error."""
    with pytest.raises(ValueError):
        setup_timezone("Invalid/Timezone")
