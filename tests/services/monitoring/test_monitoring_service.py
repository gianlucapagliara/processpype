"""Tests for the monitoring service."""

from unittest.mock import AsyncMock

import pytest

from processpype.core.models import ServiceState
from processpype.services.monitoring import MonitoringConfiguration, MonitoringService
from processpype.services.monitoring.manager import MonitoringManager


@pytest.fixture
def monitoring_config():
    """Create a monitoring configuration for testing."""
    return MonitoringConfiguration(
        enabled=True,
        interval=5.0,
        collect_cpu=True,
        collect_memory=True,
        collect_disk=True,
        disk_path="/",
    )


@pytest.fixture
def monitoring_service(monitoring_config):
    """Create a monitoring service for testing."""
    service = MonitoringService()
    service.configure(monitoring_config)
    return service


@pytest.mark.asyncio
async def test_create_manager():
    """Test creating a monitoring service manager."""
    service = MonitoringService()

    # Test the create_manager method
    manager = service.create_manager()
    assert manager is not None
    assert isinstance(manager, MonitoringManager)
    assert hasattr(manager, "logger")


@pytest.mark.asyncio
async def test_create_router():
    """Test creating a monitoring service router."""
    service = MonitoringService()

    # Test the create_router method
    router = service.create_router()
    assert router is not None
    assert router.prefix == "/services/monitoring"


@pytest.mark.asyncio
async def test_manager_property(monitoring_service):
    """Test the manager property."""
    # Test the manager property
    manager = monitoring_service.manager
    assert manager is not None
    assert isinstance(manager, MonitoringManager)
    assert hasattr(manager, "logger")


@pytest.mark.asyncio
async def test_start_stop(monitoring_service):
    """Test starting and stopping the monitoring service."""
    # Mock the manager's start and stop methods
    monitoring_service.manager.start = AsyncMock()
    monitoring_service.manager.stop = AsyncMock()
    monitoring_service.manager.set_interval = AsyncMock()
    monitoring_service.manager.set_collection_settings = AsyncMock()

    # Start the service
    await monitoring_service.start()

    # Verify the manager's start method was called
    monitoring_service.manager.start.assert_awaited_once()
    monitoring_service.manager.set_interval.assert_called_once_with(5.0)
    monitoring_service.manager.set_collection_settings.assert_called_once_with(
        collect_cpu=True,
        collect_memory=True,
        collect_disk=True,
        disk_path="/",
    )
    assert monitoring_service.status.state == ServiceState.RUNNING

    # Stop the service
    await monitoring_service.stop()

    # Verify the manager's stop method was called
    monitoring_service.manager.stop.assert_awaited_once()
    assert monitoring_service.status.state == ServiceState.STOPPED


@pytest.mark.asyncio
async def test_start_error(monitoring_service):
    """Test error handling when starting the monitoring service."""
    # Mock the manager's start method to raise an exception
    monitoring_service.manager.start = AsyncMock(side_effect=Exception("Test error"))
    monitoring_service.manager.set_interval = AsyncMock()
    monitoring_service.manager.set_collection_settings = AsyncMock()

    # Start the service and expect an exception
    with pytest.raises(Exception, match="Test error"):
        await monitoring_service.start()

    # Verify the service is in error state
    assert monitoring_service.status.state == ServiceState.ERROR
    assert "Failed to start monitoring service" in monitoring_service.status.error


@pytest.mark.asyncio
async def test_stop_error(monitoring_service):
    """Test error handling when stopping the monitoring service."""
    # Start the service first
    monitoring_service.manager.start = AsyncMock()
    monitoring_service.manager.set_interval = AsyncMock()
    monitoring_service.manager.set_collection_settings = AsyncMock()
    await monitoring_service.start()

    # Mock the manager's stop method to raise an exception
    monitoring_service.manager.stop = AsyncMock(side_effect=Exception("Test error"))

    # Stop the service
    await monitoring_service.stop()

    # Verify the service is in error state
    assert monitoring_service.status.state == ServiceState.ERROR
    assert "Failed to stop monitoring service" in monitoring_service.status.error
