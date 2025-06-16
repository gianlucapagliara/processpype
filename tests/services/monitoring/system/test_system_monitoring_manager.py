"""Tests for the monitoring manager."""

import asyncio
import logging
from unittest.mock import AsyncMock, patch

import pytest

from processpype.services.monitoring.system.manager import SystemMonitoringManager


@pytest.fixture
def logger():
    """Create a logger for testing."""
    return logging.getLogger("test_monitoring_manager")


@pytest.fixture
def monitoring_manager(logger):
    """Create a monitoring manager for testing."""
    return SystemMonitoringManager(logger)


@pytest.mark.asyncio
async def test_metrics_property(monitoring_manager):
    """Test the metrics property."""
    # Initially, metrics should be empty
    assert monitoring_manager.metrics == {}

    # Set some metrics
    monitoring_manager._metrics = {"cpu_percent": 10.0, "memory_percent": 50.0}

    # Check that metrics are returned correctly
    assert monitoring_manager.metrics == {"cpu_percent": 10.0, "memory_percent": 50.0}


@pytest.mark.asyncio
async def test_start_stop(monitoring_manager):
    """Test starting and stopping the monitoring manager."""
    # Mock the start_monitoring and stop_monitoring methods
    monitoring_manager.start_monitoring = AsyncMock()
    monitoring_manager.stop_monitoring = AsyncMock()

    # Start the manager
    await monitoring_manager.start()

    # Verify start_monitoring was called
    monitoring_manager.start_monitoring.assert_awaited_once()

    # Stop the manager
    await monitoring_manager.stop()

    # Verify stop_monitoring was called
    monitoring_manager.stop_monitoring.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_monitoring(monitoring_manager):
    """Test starting the monitoring loop."""
    # Mock asyncio.create_task
    with patch("asyncio.create_task") as mock_create_task:
        # Start monitoring
        await monitoring_manager.start_monitoring()

        # Verify create_task was called with _monitor_loop
        mock_create_task.assert_called_once()

        # Verify _monitor_task is set
        assert monitoring_manager._monitor_task is not None


@pytest.mark.asyncio
async def test_stop_monitoring_when_running(monitoring_manager):
    """Test stopping the monitoring loop when it's running."""

    # Create a real asyncio task that completes immediately
    async def dummy_coro():
        return None

    monitoring_manager._monitor_task = asyncio.create_task(dummy_coro())

    # Patch the cancel method to avoid actually cancelling the task
    with patch.object(monitoring_manager._monitor_task, "cancel") as mock_cancel:
        # Stop monitoring
        await monitoring_manager.stop_monitoring()

        # Verify task was cancelled
        mock_cancel.assert_called_once()

        # Verify _monitor_task is None
        assert monitoring_manager._monitor_task is None


@pytest.mark.asyncio
async def test_stop_monitoring_when_not_running(monitoring_manager):
    """Test stopping the monitoring loop when it's not running."""
    # Ensure _monitor_task is None
    monitoring_manager._monitor_task = None

    # Stop monitoring
    await monitoring_manager.stop_monitoring()

    # Verify _monitor_task is still None
    assert monitoring_manager._monitor_task is None


@pytest.mark.asyncio
async def test_collect_metrics(monitoring_manager):
    """Test collecting system metrics."""
    with (
        patch("psutil.cpu_percent", return_value=10.0),
        patch("psutil.virtual_memory") as mock_memory,
        patch("psutil.disk_usage") as mock_disk,
    ):
        # Configure mocks
        mock_memory.return_value.percent = 50.0
        mock_disk.return_value.percent = 30.0

        # Collect metrics
        metrics = await monitoring_manager._collect_metrics()

        # Verify metrics
        assert metrics == {
            "cpu_percent": 10.0,
            "memory_percent": 50.0,
            "disk_percent": 30.0,
        }


@pytest.mark.asyncio
async def test_monitor_loop(monitoring_manager):
    """Test the monitoring loop."""
    # Setup test data
    test_metrics = {"cpu_percent": 10.0, "memory_percent": 50.0, "disk_percent": 30.0}

    # Mock methods and sleep to run loop only once
    monitoring_manager._collect_metrics = AsyncMock(return_value=test_metrics)

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
            # Run the monitor loop for a short time
            await asyncio.wait_for(monitoring_manager._monitor_loop(), timeout=0.1)
        except (TimeoutError, asyncio.CancelledError):
            pass

        # Verify _collect_metrics was called at least once
        assert monitoring_manager._collect_metrics.await_count >= 1

        # Verify metrics were updated
        assert monitoring_manager._metrics == test_metrics


@pytest.mark.asyncio
async def test_monitor_loop_exception_handling(monitoring_manager):
    """Test exception handling in the monitoring loop."""
    # Mock _collect_metrics to raise an exception
    monitoring_manager._collect_metrics = AsyncMock(side_effect=Exception("Test error"))

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
            # Run the monitor loop for a short time
            await asyncio.wait_for(monitoring_manager._monitor_loop(), timeout=0.1)
        except (TimeoutError, asyncio.CancelledError):
            pass

        # Verify _collect_metrics was called at least once
        assert monitoring_manager._collect_metrics.await_count >= 1

        # Verify sleep was called at least once
        assert call_count >= 1
