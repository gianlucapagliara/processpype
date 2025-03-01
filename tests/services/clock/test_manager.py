"""Tests for clock service manager."""

import asyncio
import logging
from logging import Logger
from unittest.mock import AsyncMock, patch

import pytest
from chronopype.clocks.modes import ClockMode

from processpype.services.clock.config import ClockConfiguration
from processpype.services.clock.manager import ClockManager


@pytest.fixture
def logger() -> Logger:
    """Create a test logger."""
    return logging.getLogger("test")


@pytest.fixture
def manager(logger: Logger) -> ClockManager:
    """Create a test manager."""
    return ClockManager(logger)


@pytest.fixture
def config() -> ClockConfiguration:
    """Create a test configuration."""
    return ClockConfiguration(
        enabled=True,
        autostart=False,
        mode=ClockMode.REALTIME,
        tick_size=1.0,
    )


def test_initial_state(manager: ClockManager) -> None:
    """Test initial manager state."""
    assert manager._clock is None
    assert manager._config is None


def test_configuration(manager: ClockManager, config: ClockConfiguration) -> None:
    """Test manager configuration."""
    manager.set_configuration(config)
    assert manager._clock is not None
    assert manager._config is not None
    assert manager._config.clock_mode == config.mode
    assert manager._config.tick_size == config.tick_size


@pytest.mark.asyncio
async def test_start_without_config(manager: ClockManager) -> None:
    """Test starting without configuration."""
    await manager.start()
    # Should set the clock to the default configuration
    assert (
        manager._clock.config == manager.get_default_configuration().get_clock_config()
    )


@pytest.mark.asyncio
async def test_stop_without_config(manager: ClockManager) -> None:
    """Test stopping without configuration."""
    await manager.stop()
    # Should return without error
    assert manager._clock is None


def test_status_without_config(manager: ClockManager) -> None:
    """Test getting status without configuration."""
    status = manager.get_clock_status()
    assert status == {
        "configured": False,
        "running": False,
    }


@pytest.mark.asyncio
async def test_realtime_clock_lifecycle(
    manager: ClockManager, config: ClockConfiguration
) -> None:
    """Test realtime clock lifecycle."""
    manager.set_configuration(config)

    # Create a mock context manager
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = manager._clock
    mock_context.__aexit__.return_value = None

    # Mock both the clock instance and its run method
    with (
        patch.object(
            manager._clock, "__aenter__", return_value=mock_context.__aenter__()
        ),
        patch.object(
            manager._clock, "__aexit__", return_value=mock_context.__aexit__()
        ),
        patch.object(manager._clock, "run") as mock_run,
    ):
        await manager.start()
        # Wait for the task to complete
        if manager._clock_task:
            try:
                await asyncio.wait_for(manager._clock_task, timeout=1.0)
            except TimeoutError:
                pass  # Task may run indefinitely, we just need to ensure it started
        mock_run.assert_called_once()

    # Get status after starting
    status = manager.get_clock_status()
    assert status["configured"] is True
    assert status["mode"] == ClockMode.REALTIME
    assert status["tick_size"] == 1.0

    # Stop the clock
    await manager.stop()


@pytest.mark.asyncio
async def test_backtest_clock_lifecycle(
    manager: ClockManager, config: ClockConfiguration
) -> None:
    """Test backtest clock lifecycle."""
    config = ClockConfiguration(
        enabled=True,
        autostart=False,
        mode=ClockMode.BACKTEST,
        tick_size=0.5,
        start_time=1000.0,
        end_time=2000.0,
    )
    manager.set_configuration(config)

    # Create a mock context manager
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = manager._clock
    mock_context.__aexit__.return_value = None

    # Mock both the clock instance and its run method
    with (
        patch.object(
            manager._clock, "__aenter__", return_value=mock_context.__aenter__()
        ),
        patch.object(
            manager._clock, "__aexit__", return_value=mock_context.__aexit__()
        ),
        patch.object(manager._clock, "run") as mock_run,
    ):
        await manager.start()
        # Wait for the task to complete
        if manager._clock_task:
            try:
                await asyncio.wait_for(manager._clock_task, timeout=1.0)
            except TimeoutError:
                pass  # Task may run indefinitely, we just need to ensure it started
        mock_run.assert_called_once()

    # Get status after starting
    status = manager.get_clock_status()
    assert status["configured"] is True
    assert status["mode"] == ClockMode.BACKTEST
    assert status["tick_size"] == 0.5

    # Stop the clock
    await manager.stop()
