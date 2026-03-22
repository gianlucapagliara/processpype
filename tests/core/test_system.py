"""Unit tests for system utilities."""

import os
import sys
from unittest.mock import patch

import pytest

from processpype.environment.system import setup_timezone


def test_default_timezone() -> None:
    """Test that setup_timezone defaults to UTC."""
    with patch("time.tzset"):
        setup_timezone()
        assert os.environ["TZ"] == "UTC"


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

    setup_timezone(test_tz)
    assert os.environ["TZ"] == test_tz


def test_setup_timezone_error() -> None:
    """Test setup timezone error."""
    with pytest.raises(ValueError):
        setup_timezone("Invalid/Timezone")
