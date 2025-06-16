"""Tests for the Cronitor service."""

from unittest.mock import AsyncMock

import pytest

from processpype.core.models import ServiceState
from processpype.services.monitoring.cronitor import (
    CronitorConfiguration,
    CronitorService,
)
from processpype.services.monitoring.cronitor.manager import CronitorManager


@pytest.fixture
def cronitor_config() -> CronitorConfiguration:
    """Create a Cronitor configuration for testing."""
    return CronitorConfiguration(
        enabled=True,
        api_key="test_api_key",
        monitor_key="test_monitor_key",
        interval=30.0,
        state="run",
        environment="test",
        series="test_series",
        metrics={"test_metric": 10.0},
    )


@pytest.fixture
def cronitor_service(cronitor_config: CronitorConfiguration) -> CronitorService:
    """Create a Cronitor service for testing."""
    service = CronitorService()
    service.configure(cronitor_config)
    return service


@pytest.mark.asyncio
async def test_create_manager() -> None:
    """Test creating a Cronitor service manager."""
    service = CronitorService()

    # Test the create_manager method
    manager = service.create_manager()
    assert manager is not None
    assert isinstance(manager, CronitorManager)
    assert hasattr(manager, "logger")


@pytest.mark.asyncio
async def test_create_router() -> None:
    """Test creating a Cronitor service router."""
    service = CronitorService()

    # Test the create_router method
    router = service.create_router()
    assert router is not None
    assert router.prefix == "/services/cronitor"


@pytest.mark.asyncio
async def test_manager_property(cronitor_service: CronitorService) -> None:
    """Test the manager property."""
    # Test the manager property
    manager = cronitor_service.manager
    assert manager is not None
    assert isinstance(manager, CronitorManager)
    assert hasattr(manager, "logger")


@pytest.mark.asyncio
async def test_start_stop(cronitor_service: CronitorService) -> None:
    """Test starting and stopping the Cronitor service."""
    # Mock the manager's methods
    cronitor_service.manager.start = AsyncMock()
    cronitor_service.manager.stop = AsyncMock()
    cronitor_service.manager.set_api_key = AsyncMock()
    cronitor_service.manager.set_monitor_key = AsyncMock()
    cronitor_service.manager.set_interval = AsyncMock()
    cronitor_service.manager.set_state = AsyncMock()
    cronitor_service.manager.set_environment = AsyncMock()
    cronitor_service.manager.set_series = AsyncMock()
    cronitor_service.manager.set_metrics = AsyncMock()

    # Start the service
    await cronitor_service.start()

    # Verify the manager's methods were called
    cronitor_service.manager.start.assert_awaited_once()
    cronitor_service.manager.set_api_key.assert_called_once_with("test_api_key")
    cronitor_service.manager.set_monitor_key.assert_called_once_with("test_monitor_key")
    cronitor_service.manager.set_interval.assert_called_once_with(30.0)
    cronitor_service.manager.set_state.assert_called_once_with("run")
    cronitor_service.manager.set_environment.assert_called_once_with("test")
    cronitor_service.manager.set_series.assert_called_once_with("test_series")
    cronitor_service.manager.set_metrics.assert_called_once_with({"test_metric": 10.0})
    assert cronitor_service.status.state == ServiceState.RUNNING

    # Stop the service
    await cronitor_service.stop()

    # Verify the manager's stop method was called
    cronitor_service.manager.stop.assert_awaited_once()
    assert cronitor_service.status.state == ServiceState.STOPPED


@pytest.mark.asyncio
async def test_start_error(cronitor_service: CronitorService) -> None:
    """Test error handling when starting the Cronitor service."""
    # Mock the manager's start method to raise an exception
    cronitor_service.manager.start = AsyncMock(side_effect=Exception("Test error"))
    cronitor_service.manager.set_api_key = AsyncMock()
    cronitor_service.manager.set_monitor_key = AsyncMock()
    cronitor_service.manager.set_interval = AsyncMock()
    cronitor_service.manager.set_state = AsyncMock()
    cronitor_service.manager.set_environment = AsyncMock()
    cronitor_service.manager.set_series = AsyncMock()
    cronitor_service.manager.set_metrics = AsyncMock()

    # Start the service and expect an exception
    with pytest.raises(Exception, match="Test error"):
        await cronitor_service.start()

    # Verify the service is in error state
    assert cronitor_service.status.state == ServiceState.ERROR
    assert "Failed to start cronitor service" in cronitor_service.status.error


@pytest.mark.asyncio
async def test_stop_error(cronitor_service: CronitorService) -> None:
    """Test error handling when stopping the Cronitor service."""
    # Start the service first
    cronitor_service.manager.start = AsyncMock()
    cronitor_service.manager.set_api_key = AsyncMock()
    cronitor_service.manager.set_monitor_key = AsyncMock()
    cronitor_service.manager.set_interval = AsyncMock()
    cronitor_service.manager.set_state = AsyncMock()
    cronitor_service.manager.set_environment = AsyncMock()
    cronitor_service.manager.set_series = AsyncMock()
    cronitor_service.manager.set_metrics = AsyncMock()
    await cronitor_service.start()

    # Mock the manager's stop method to raise an exception
    cronitor_service.manager.stop = AsyncMock(side_effect=Exception("Test error"))

    # Stop the service
    await cronitor_service.stop()

    # Verify the service is in error state
    assert cronitor_service.status.state == ServiceState.ERROR
    assert "Failed to stop cronitor service" in cronitor_service.status.error


@pytest.mark.asyncio
async def test_trigger_ping(cronitor_service: CronitorService) -> None:
    """Test triggering a ping manually."""
    # Mock the manager's _ping_cronitor method
    cronitor_service.manager._ping_cronitor = AsyncMock()

    # Trigger a ping
    result = await cronitor_service.trigger_ping()

    # Verify the manager's _ping_cronitor method was called
    cronitor_service.manager._ping_cronitor.assert_awaited_once()
    assert result == {"status": "ping sent"}
