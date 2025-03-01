"""Tests for clock service configuration."""

import pytest
from chronopype.clocks.modes import ClockMode

from processpype.services.clock.config import ClockConfiguration


def test_default_configuration() -> None:
    """Test default configuration values."""
    config = ClockConfiguration()
    assert config.mode == ClockMode.REALTIME
    assert config.tick_size == 1.0
    assert config.start_time is None
    assert config.end_time is None


def test_custom_configuration() -> None:
    """Test custom configuration values."""
    config = ClockConfiguration(
        mode=ClockMode.BACKTEST,
        tick_size=0.5,
        start_time=1000.0,
        end_time=2000.0,
    )
    assert config.mode == ClockMode.BACKTEST
    assert config.tick_size == 0.5
    assert config.start_time == 1000.0
    assert config.end_time == 2000.0


def test_invalid_tick_size() -> None:
    """Test validation of tick size."""
    with pytest.raises(ValueError):
        ClockConfiguration(tick_size=0.0)  # Zero tick size

    with pytest.raises(ValueError):
        ClockConfiguration(tick_size=-1.0)  # Negative tick size
