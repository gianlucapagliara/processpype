"""Unit tests for application manager."""

import logging
from typing import Protocol, runtime_checkable
from unittest.mock import MagicMock

import pytest

from processpype.core.configuration.models import (
    ApplicationConfiguration,
    ServiceConfiguration,
)
from processpype.core.manager import ApplicationManager
from processpype.core.models import ServiceState
from processpype.core.service import Service
from processpype.core.service.manager import ServiceManager
from processpype.core.service.router import ServiceRouter


@runtime_checkable
class TestableService(Protocol):
    """Protocol for testable service interface."""

    @property
    def start_called(self) -> bool:
        """Check if start was called."""
        ...

    @property
    def stop_called(self) -> bool:
        """Check if stop was called."""
        ...

    @property
    def configure_called(self) -> bool:
        """Check if configure was called."""
        ...

    @property
    def config(self) -> ServiceConfiguration | None:
        """Get service configuration."""
        ...


class MockService(Service):
    """Mock service for testing."""

    def __init__(self, name: str | None = None):
        """Initialize mock service.

        Args:
            name: Optional service name
        """
        super().__init__(name)
        # Test tracking attributes
        self._start_called = False
        self._stop_called = False
        self._configure_called = False
        self._config: ServiceConfiguration | None = None
        self._logger = logging.getLogger(f"test.service.{self.name or 'mock'}")

    @property
    def start_called(self) -> bool:
        """Check if start was called."""
        return self._start_called

    @property
    def stop_called(self) -> bool:
        """Check if stop was called."""
        return self._stop_called

    @property
    def configure_called(self) -> bool:
        """Check if configure was called."""
        return self._configure_called

    @property
    def config(self) -> ServiceConfiguration | None:
        """Get service configuration."""
        return self._config

    async def start(self) -> None:
        """Start the mock service."""
        self._start_called = True
        self.status.state = ServiceState.RUNNING

    async def stop(self) -> None:
        """Stop the mock service."""
        self._stop_called = True
        self.status.state = ServiceState.STOPPED

    def configure(self, config: ServiceConfiguration) -> None:
        """Configure the mock service."""
        self._configure_called = True
        self._config = config

    def create_manager(self) -> ServiceManager:
        """Create a mock service manager."""
        if self._logger is None:
            self._logger = logging.getLogger(f"test.service.{self.name or 'mock'}")
        return ServiceManager(self._logger)

    def create_router(self) -> ServiceRouter:
        """Create a mock service router."""
        return ServiceRouter(
            name=self.name,
            get_status=lambda: self.status,
        )


@pytest.fixture
def logger() -> logging.Logger:
    """Create test logger."""
    return logging.getLogger("test")


@pytest.fixture
def app_config() -> ApplicationConfiguration:
    """Create test application configuration."""
    return ApplicationConfiguration(
        title="Test App",
        version="1.0.0",
        host="localhost",
        port=8080,
        debug=True,
        environment="testing",
        services={
            "test_service": ServiceConfiguration(
                enabled=True,
                autostart=True,
                metadata={"key": "value"},
            )
        },
    )


@pytest.fixture
def manager(
    logger: logging.Logger, app_config: ApplicationConfiguration
) -> ApplicationManager:
    """Create test manager instance."""
    return ApplicationManager(logger, app_config)


async def test_manager_initialization(manager: ApplicationManager) -> None:
    """Test manager initialization."""
    assert manager.state == ServiceState.STOPPED
    assert len(manager.services) == 0


async def test_service_registration(manager: ApplicationManager) -> None:
    """Test service registration."""
    service = manager.register_service(MockService, name="test_service")
    assert isinstance(service, MockService)

    assert service.name == "test_service"
    assert service.name in manager.services
    assert isinstance(service, TestableService)
    assert service.configure_called
    assert service.config is not None
    assert service.config.enabled


async def test_service_registration_duplicate(manager: ApplicationManager) -> None:
    """Test duplicate service registration."""
    manager.register_service(MockService, name="test_service")

    with pytest.raises(ValueError):
        manager.register_service(MockService, name="test_service")


async def test_service_registration_without_config(manager: ApplicationManager) -> None:
    """Test service registration without configuration."""
    service = manager.register_service(MockService, name="new_service")
    assert isinstance(service, MockService)

    assert service.name == "new_service"
    assert isinstance(service, TestableService)
    assert not service.configure_called
    assert service.config is None


async def test_get_service(manager: ApplicationManager) -> None:
    """Test service retrieval."""
    service = manager.register_service(MockService, name="test_service")

    retrieved = manager.get_service("test_service")
    assert retrieved == service

    assert manager.get_service("nonexistent") is None


async def test_start_service(manager: ApplicationManager) -> None:
    """Test starting a service."""
    service = manager.register_service(MockService, name="test_service")
    assert isinstance(service, MockService)
    await manager.start_service("test_service")

    assert isinstance(service, TestableService)
    assert service.start_called
    assert service.status.state.value == "running"


async def test_start_nonexistent_service(manager: ApplicationManager) -> None:
    """Test starting a non-existent service."""
    with pytest.raises(ValueError):
        await manager.start_service("nonexistent")


async def test_stop_service(manager: ApplicationManager) -> None:
    """Test stopping a service."""
    service = manager.register_service(MockService, name="test_service")
    assert isinstance(service, MockService)
    await manager.start_service("test_service")
    await manager.stop_service("test_service")

    assert isinstance(service, TestableService)
    assert service.stop_called
    assert service.status.state.value == "stopped"


async def test_stop_nonexistent_service(manager: ApplicationManager) -> None:
    """Test stopping a non-existent service."""
    with pytest.raises(ValueError):
        await manager.stop_service("nonexistent")


async def test_start_enabled_services(manager: ApplicationManager) -> None:
    """Test starting enabled services."""
    service1 = manager.register_service(MockService, name="test_service")
    service2 = manager.register_service(MockService, name="disabled_service")
    assert isinstance(service1, MockService)
    assert isinstance(service2, MockService)

    await manager.start_enabled_services()

    assert isinstance(service1, TestableService)
    assert isinstance(service2, TestableService)
    assert service1.start_called
    assert not service2.start_called


async def test_start_enabled_services_error_handling(
    manager: ApplicationManager,
    logger: logging.Logger,
) -> None:
    """Test error handling when starting enabled services."""
    # Create a service that raises an exception on start
    error_service = MockService(name="test_service")
    error_service._start_called = False  # Reset the flag
    error_service.start = MagicMock(side_effect=Exception("Start failed"))  # type: ignore[method-assign]
    manager._services["test_service"] = error_service

    # Should not raise exception
    await manager.start_enabled_services()


async def test_stop_all_services(manager: ApplicationManager) -> None:
    """Test stopping all services."""
    service1 = manager.register_service(MockService, name="service1")
    service2 = manager.register_service(MockService, name="service2")
    assert isinstance(service1, MockService)
    assert isinstance(service2, MockService)

    await manager.start_enabled_services()
    await manager.stop_all_services()

    assert isinstance(service1, TestableService)
    assert isinstance(service2, TestableService)
    assert service1.stop_called
    assert service2.stop_called


async def test_stop_all_services_error_handling(
    manager: ApplicationManager,
    logger: logging.Logger,
) -> None:
    """Test error handling when stopping all services."""
    # Create a service that raises an exception on stop
    error_service = MockService(name="test_service")
    error_service._stop_called = False  # Reset the flag
    error_service.stop = MagicMock(side_effect=Exception("Stop failed"))  # type: ignore[method-assign]
    manager._services["test_service"] = error_service

    # Should not raise exception
    await manager.stop_all_services()


def test_set_state(manager: ApplicationManager) -> None:
    """Test setting application state."""
    manager.set_state(ServiceState.RUNNING)
    assert manager.state.value == "running"

    manager.set_state(ServiceState.STOPPED)
    assert manager.state.value == "stopped"
