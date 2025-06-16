"""Tests for the Cronitor manager."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from processpype.services.monitoring.cronitor.manager import CronitorManager


@pytest.fixture
def logger() -> logging.Logger:
    """Create a logger for testing."""
    return logging.getLogger("test_cronitor_manager")


@pytest.fixture
def cronitor_manager(logger: logging.Logger) -> CronitorManager:
    """Create a Cronitor manager for testing."""
    return CronitorManager(logger)


@pytest.mark.asyncio
async def test_set_api_key(cronitor_manager: CronitorManager) -> None:
    """Test setting the API key."""
    with patch(
        "processpype.services.monitoring.cronitor.manager.cronitor"
    ) as mock_cronitor:
        cronitor_manager.set_api_key("test_api_key")
        assert cronitor_manager._api_key == "test_api_key"
        assert mock_cronitor.api_key == "test_api_key"


@pytest.mark.asyncio
async def test_set_monitor_key(cronitor_manager: CronitorManager) -> None:
    """Test setting the monitor key."""
    cronitor_manager.set_monitor_key("test_monitor_key")
    assert cronitor_manager._monitor_key == "test_monitor_key"


@pytest.mark.asyncio
async def test_set_interval(cronitor_manager: CronitorManager) -> None:
    """Test setting the interval."""
    cronitor_manager.set_interval(30.0)
    assert cronitor_manager._interval == 30.0


@pytest.mark.asyncio
async def test_set_state(cronitor_manager: CronitorManager) -> None:
    """Test setting the state."""
    cronitor_manager.set_state("complete")
    assert cronitor_manager._state == "complete"


@pytest.mark.asyncio
async def test_set_environment(cronitor_manager: CronitorManager) -> None:
    """Test setting the environment."""
    cronitor_manager.set_environment("test")
    assert cronitor_manager._environment == "test"


@pytest.mark.asyncio
async def test_set_series(cronitor_manager: CronitorManager) -> None:
    """Test setting the series."""
    cronitor_manager.set_series("test_series")
    assert cronitor_manager._series == "test_series"


@pytest.mark.asyncio
async def test_set_metrics(cronitor_manager: CronitorManager) -> None:
    """Test setting the metrics."""
    metrics = {"test_metric": 10.0}
    cronitor_manager.set_metrics(metrics)
    assert cronitor_manager._metrics == metrics


@pytest.mark.asyncio
async def test_start_stop(cronitor_manager: CronitorManager) -> None:
    """Test starting and stopping the Cronitor manager."""
    # Mock the start_pinging and stop_pinging methods
    cronitor_manager.start_pinging = AsyncMock()
    cronitor_manager.stop_pinging = AsyncMock()

    # Start the manager
    await cronitor_manager.start()

    # Verify start_pinging was called
    cronitor_manager.start_pinging.assert_awaited_once()

    # Stop the manager
    await cronitor_manager.stop()

    # Verify stop_pinging was called
    cronitor_manager.stop_pinging.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_pinging_with_missing_keys(
    cronitor_manager: CronitorManager,
) -> None:
    """Test starting the pinging loop with missing API key or monitor key."""
    # Ensure API key and monitor key are empty
    cronitor_manager._api_key = ""
    cronitor_manager._monitor_key = ""

    # Start pinging
    await cronitor_manager.start_pinging()

    # Verify _ping_task is None
    assert cronitor_manager._ping_task is None


@pytest.mark.asyncio
async def test_start_pinging(cronitor_manager: CronitorManager) -> None:
    """Test starting the pinging loop."""
    # Set API key and monitor key
    cronitor_manager._api_key = "test_api_key"
    cronitor_manager._monitor_key = "test_monitor_key"

    # Mock asyncio.create_task
    with patch("asyncio.create_task") as mock_create_task:
        # Start pinging
        await cronitor_manager.start_pinging()

        # Verify create_task was called with _ping_loop
        mock_create_task.assert_called_once()

        # Verify _ping_task is set
        assert cronitor_manager._ping_task is not None


@pytest.mark.asyncio
async def test_stop_pinging_when_running(cronitor_manager: CronitorManager) -> None:
    """Test stopping the pinging loop when it's running."""

    # Create a real asyncio task that completes immediately
    async def dummy_coro():
        return None

    cronitor_manager._ping_task = asyncio.create_task(dummy_coro())

    # Patch the cancel method to avoid actually cancelling the task
    with patch.object(cronitor_manager._ping_task, "cancel") as mock_cancel:
        # Stop pinging
        await cronitor_manager.stop_pinging()

        # Verify task was cancelled
        mock_cancel.assert_called_once()

        # Verify _ping_task is None
        assert cronitor_manager._ping_task is None


@pytest.mark.asyncio
async def test_stop_pinging_when_not_running(cronitor_manager: CronitorManager) -> None:
    """Test stopping the pinging loop when it's not running."""
    # Ensure _ping_task is None
    cronitor_manager._ping_task = None

    # Stop pinging
    await cronitor_manager.stop_pinging()

    # Verify _ping_task is still None
    assert cronitor_manager._ping_task is None


@pytest.mark.asyncio
async def test_ping_cronitor(cronitor_manager: CronitorManager) -> None:
    """Test sending a ping to Cronitor."""
    # Set up test data
    cronitor_manager._monitor_key = "test_monitor_key"
    cronitor_manager._state = "run"
    cronitor_manager._environment = "test"
    cronitor_manager._series = "test_series"
    cronitor_manager._metrics = {"test_metric": 10.0}

    # Mock the cronitor.Monitor class
    with patch(
        "processpype.services.monitoring.cronitor.manager.cronitor"
    ) as mock_cronitor:
        # Create a mock monitor instance
        mock_monitor = MagicMock()
        mock_cronitor.Monitor.return_value = mock_monitor
        mock_monitor.ping = MagicMock()

        # Mock asyncio.to_thread
        with patch("asyncio.to_thread", AsyncMock()) as mock_to_thread:
            # Send ping
            await cronitor_manager._ping_cronitor()

            # Verify Monitor was created with the correct key
            mock_cronitor.Monitor.assert_called_once_with("test_monitor_key")

            # Verify to_thread was called with the correct arguments
            mock_to_thread.assert_awaited_once_with(
                mock_monitor.ping,
                state="run",
                env="test",
                series="test_series",
                **{"metric[test_metric]": 10.0},
            )


@pytest.mark.asyncio
async def test_ping_cronitor_exception(cronitor_manager: CronitorManager) -> None:
    """Test exception handling when sending a ping to Cronitor."""
    # Set up test data
    cronitor_manager._monitor_key = "test_monitor_key"

    # Mock the cronitor.Monitor class to raise an exception
    with patch(
        "processpype.services.monitoring.cronitor.manager.cronitor"
    ) as mock_cronitor:
        mock_cronitor.Monitor.side_effect = Exception("Test error")

        # Send ping
        await cronitor_manager._ping_cronitor()
        # No exception should be raised, it should be caught and logged


@pytest.mark.asyncio
async def test_ping_loop(cronitor_manager: CronitorManager) -> None:
    """Test the pinging loop."""
    # Mock _ping_cronitor
    cronitor_manager._ping_cronitor = AsyncMock()

    # Create a mock sleep function that raises CancelledError after first call
    sleep_called = False

    async def mock_sleep(seconds):
        nonlocal sleep_called
        if not sleep_called:
            sleep_called = True
            return None
        else:
            raise asyncio.CancelledError()

    with patch("asyncio.sleep", side_effect=mock_sleep):
        try:
            # Run the ping loop for a short time
            await asyncio.wait_for(cronitor_manager._ping_loop(), timeout=0.1)
        except (TimeoutError, asyncio.CancelledError):
            pass

        # Verify _ping_cronitor was called at least once
        assert cronitor_manager._ping_cronitor.await_count >= 1


@pytest.mark.asyncio
async def test_ping_loop_exception_handling(cronitor_manager: CronitorManager) -> None:
    """Test exception handling in the pinging loop."""
    # Mock _ping_cronitor to raise an exception
    cronitor_manager._ping_cronitor = AsyncMock(side_effect=Exception("Test error"))

    # Create a mock sleep function that raises CancelledError after first call
    call_count = 0

    async def mock_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            raise asyncio.CancelledError()
        return None

    with patch("asyncio.sleep", side_effect=mock_sleep):
        try:
            # Run the ping loop for a short time
            await asyncio.wait_for(cronitor_manager._ping_loop(), timeout=0.1)
        except (TimeoutError, asyncio.CancelledError):
            pass

        # Verify _ping_cronitor was called at least once
        assert cronitor_manager._ping_cronitor.await_count >= 1

        # Verify sleep was called at least once
        assert call_count >= 1
