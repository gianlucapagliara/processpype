"""Unit tests for core service components."""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import Field

from processpype.core.configuration.models import ServiceConfiguration
from processpype.core.models import ServiceState
from processpype.core.service import Service
from processpype.core.service.manager import ServiceManager
from processpype.core.service.router import ServiceRouter


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
