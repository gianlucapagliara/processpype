"""Unit tests for core service components."""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import Field

from processpype.config.models import ServiceConfiguration
from processpype.server.service_router import ServiceRouter
from processpype.service.base import Service
from processpype.service.manager import ServiceManager
from processpype.service.models import ServiceState


@pytest.fixture
def event_loop():
    """Create an event loop for tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class MockServiceConfiguration(ServiceConfiguration):
    """Mock service configuration."""

    metadata: dict[str, Any] = Field(default_factory=dict)


class MockServiceManager(ServiceManager):
    """Test service manager implementation."""

    def __init__(self, logger: logging.Logger):
        super().__init__(logger)
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        """Start the test service manager."""
        self.started = True

    async def stop(self) -> None:
        """Stop the test service manager."""
        self.stopped = True


class MockService(Service):
    """Test service implementation."""

    configuration_class = MockServiceConfiguration

    if TYPE_CHECKING:
        manager: MockServiceManager

    def __init__(self, name: str | None = None):
        self.manager_created = False
        self.router_created = False
        super().__init__(name)

    def create_manager(self) -> MockServiceManager:
        """Create test service manager."""
        self.manager_created = True
        return MockServiceManager(logging.getLogger("test.manager"))

    def create_router(self) -> ServiceRouter:
        """Create a mock service router."""
        self.router_created = True
        return ServiceRouter(
            name=self.name,
            get_status=lambda: self.status,
        )


@pytest.fixture
def service() -> MockService:
    """Create test service instance."""
    return MockService()


def test_service_initialization() -> None:
    """Test service initialization."""
    service = MockService("test_service")
    assert service.name == "test_service"
    assert service.status.state == ServiceState.INITIALIZED
    assert service.manager_created
    assert service.router_created


def test_service_name_generation() -> None:
    """Test service name generation from class name."""
    service = MockService()
    assert service.name == "mock"


def test_service_logger() -> None:
    """Test service logger initialization."""
    service = MockService()
    assert service.logger is not None
    assert isinstance(service.logger, logging.Logger)
    assert service.logger.name == f"processpype.services.{service.name}"


def test_service_configuration() -> None:
    """Test service configuration."""
    service = MockService()
    config = MockServiceConfiguration(
        autostart=True,
        metadata={"key": "value"},
    )

    service.configure(config)
    assert service.config == config
    assert service.status.metadata == config.model_dump(mode="json")


def test_service_error_handling() -> None:
    """Test service error handling."""
    service = MockService()
    error_msg = "Test error"

    service.set_error(error_msg)
    assert service.status.error == error_msg


@pytest.mark.asyncio
async def test_service_lifecycle() -> None:
    """Test service lifecycle management."""
    service = MockService()

    # Configure the service before starting
    config = MockServiceConfiguration(
        autostart=True,
        metadata={"key": "value"},
    )
    service.configure(config)

    # Test start
    await service.start()
    assert service.status.state.value == "running"
    assert service.status.error is None
    assert service.manager.started is True

    # Test stop
    await service.stop()
    assert service.status.state.value == "stopped"
    assert service.manager.stopped is True


def test_service_manager() -> None:
    """Test service manager creation and access."""
    service = MockService()
    assert service.manager is not None
    assert isinstance(service.manager, MockServiceManager)


def test_service_router() -> None:
    """Test service router creation and access."""
    service = MockService()
    assert service.router is not None
    assert isinstance(service.router, ServiceRouter)
    assert service.router.prefix == f"/services/{service.name}"


def test_service_status() -> None:
    """Test service status management."""
    service = MockService()
    assert service.status is not None
    assert service.status.state == ServiceState.INITIALIZED
    assert service.status.error is None
    assert service.status.metadata == {}


@pytest.mark.asyncio
async def test_service_start_without_configuration() -> None:
    """Test that starting a service that requires configuration raises ConfigurationError."""
    from processpype.service.base import ConfigurationError

    service = MockService()
    assert service.requires_configuration()
    assert not service.status.is_configured

    with pytest.raises(ConfigurationError, match="must be configured"):
        await service.start()
    assert service.status.state == ServiceState.ERROR


@pytest.mark.asyncio
async def test_service_start_from_invalid_state() -> None:
    """Test that starting a service from RUNNING state raises RuntimeError."""
    service = MockService()
    config = MockServiceConfiguration(autostart=False, metadata={})
    service.configure(config)
    await service.start()
    assert service.status.state == ServiceState.RUNNING

    with pytest.raises(RuntimeError, match="cannot be started"):
        await service.start()


@pytest.mark.asyncio
async def test_service_start_manager_error() -> None:
    """Test error handling when manager.start() raises."""
    service = MockService()
    config = MockServiceConfiguration(autostart=False, metadata={})
    service.configure(config)

    service.manager.start = _raise_start  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="manager boom"):
        await service.start()
    assert service.status.state == ServiceState.ERROR


async def _raise_start() -> None:
    raise RuntimeError("manager boom")


@pytest.mark.asyncio
async def test_service_stop_manager_error() -> None:
    """Test error handling when manager.stop() raises."""
    service = MockService()
    config = MockServiceConfiguration(autostart=False, metadata={})
    service.configure(config)
    await service.start()

    async def _raise_stop() -> None:
        raise RuntimeError("stop boom")

    service.manager.stop = _raise_stop  # type: ignore[method-assign]

    await service.stop()
    assert service.status.state == ServiceState.ERROR
    assert "stop boom" in (service.status.error or "")


@pytest.mark.asyncio
async def test_autostart_with_running_loop() -> None:
    """Test that configure with autostart=True creates a task on the running loop."""
    service = MockService()
    config = MockServiceConfiguration(autostart=True, metadata={})

    # We're already inside a running event loop (pytest-asyncio), so autostart
    # should schedule a task.
    service.configure(config)
    assert service.status.is_configured

    # Give the autostart task a chance to run
    await asyncio.sleep(0.05)
    assert service.status.state == ServiceState.RUNNING


def test_autostart_without_running_loop() -> None:
    """Test that configure with autostart=True warns when no event loop is running."""
    service = MockService()
    config = MockServiceConfiguration(autostart=True, metadata={})

    # Outside of an async context there is no running loop
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        service.configure(config)

    # Service should still be configured, but not running
    assert service.status.is_configured
    assert service.status.state != ServiceState.RUNNING


@pytest.mark.asyncio
async def test_autostart_done_callback_cancelled() -> None:
    """Test _on_autostart_done handles a cancelled task."""
    service = MockService()

    task = asyncio.get_event_loop().create_task(asyncio.sleep(10))
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Should not raise
    service._on_autostart_done(task)


@pytest.mark.asyncio
async def test_autostart_done_callback_exception() -> None:
    """Test _on_autostart_done handles a failed task."""
    service = MockService()

    async def _fail() -> None:
        raise ValueError("boom")

    task = asyncio.get_event_loop().create_task(_fail())
    try:
        await task
    except ValueError:
        pass

    service._on_autostart_done(task)
    assert service.status.state == ServiceState.ERROR
    assert "boom" in (service.status.error or "")


@pytest.mark.asyncio
async def test_configure_and_start() -> None:
    """Test configure_and_start configures and starts the service."""
    service = MockService()
    config = MockServiceConfiguration(autostart=False, metadata={"x": 1})

    result = await service.configure_and_start(config)
    assert result is service
    assert service.status.is_configured
    assert service.status.state == ServiceState.RUNNING


def test_validate_configuration_none() -> None:
    """Test _validate_configuration raises when config is None."""
    from processpype.service.base import ConfigurationError

    service = MockService()
    assert service._config is None

    with pytest.raises(ConfigurationError, match="has no configuration"):
        service._validate_configuration()
    assert not service.status.is_configured
