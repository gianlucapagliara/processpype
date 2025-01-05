"""Unit tests for application manager."""

import logging
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


class MockService(Service):
    """Mock service for testing."""

    def __init__(self, name: str | None = None):
        super().__init__(name)
        self.start_called = False
        self.stop_called = False
        self.configure_called = False
        self.config = None
        self._logger = logging.getLogger(f"test.service.{self.name or 'mock'}")

    async def start(self) -> None:
        """Start the mock service."""
        self.start_called = True
        self.status.state = ServiceState.RUNNING

    async def stop(self) -> None:
        """Stop the mock service."""
        self.stop_called = True
        self.status.state = ServiceState.STOPPED

    def configure(self, config: ServiceConfiguration) -> None:
        """Configure the mock service."""
        self.configure_called = True
        self.config = config

    def create_manager(self) -> ServiceManager:
        """Create a mock service manager."""
        return ServiceManager(self._logger)

    def create_router(self) -> ServiceRouter | None:
        """Create a mock service router."""
        return None


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

    assert service.name == "test_service"
    assert service.name in manager.services
    assert isinstance(service, MockService)
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

    assert service.name == "new_service"
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
    await manager.start_service("test_service")

    assert service.start_called
    assert service.status.state == ServiceState.RUNNING


async def test_start_nonexistent_service(manager: ApplicationManager) -> None:
    """Test starting a non-existent service."""
    with pytest.raises(ValueError):
        await manager.start_service("nonexistent")


async def test_stop_service(manager: ApplicationManager) -> None:
    """Test stopping a service."""
    service = manager.register_service(MockService, name="test_service")
    await manager.start_service("test_service")
    await manager.stop_service("test_service")

    assert service.stop_called
    assert service.status.state == ServiceState.STOPPED


async def test_stop_nonexistent_service(manager: ApplicationManager) -> None:
    """Test stopping a non-existent service."""
    with pytest.raises(ValueError):
        await manager.stop_service("nonexistent")


async def test_start_enabled_services(manager: ApplicationManager) -> None:
    """Test starting enabled services."""
    service1 = manager.register_service(MockService, name="test_service")
    service2 = manager.register_service(MockService, name="disabled_service")

    await manager.start_enabled_services()

    assert service1.start_called
    assert not service2.start_called


async def test_start_enabled_services_error_handling(
    manager: ApplicationManager,
    logger: logging.Logger,
) -> None:
    """Test error handling when starting enabled services."""
    # Create a service that raises an exception on start
    error_service = MockService(name="test_service")
    error_service.start = MagicMock(side_effect=Exception("Start failed"))
    manager._services["test_service"] = error_service

    # Should not raise exception
    await manager.start_enabled_services()


async def test_stop_all_services(manager: ApplicationManager) -> None:
    """Test stopping all services."""
    service1 = manager.register_service(MockService, name="service1")
    service2 = manager.register_service(MockService, name="service2")

    await manager.start_enabled_services()
    await manager.stop_all_services()

    assert service1.stop_called
    assert service2.stop_called


async def test_stop_all_services_error_handling(
    manager: ApplicationManager,
    logger: logging.Logger,
) -> None:
    """Test error handling when stopping all services."""
    # Create a service that raises an exception on stop
    error_service = MockService(name="test_service")
    error_service.stop = MagicMock(side_effect=Exception("Stop failed"))
    manager._services["test_service"] = error_service

    # Should not raise exception
    await manager.stop_all_services()


def test_set_state(manager: ApplicationManager) -> None:
    """Test setting application state."""
    manager.set_state(ServiceState.RUNNING)
    assert manager.state == ServiceState.RUNNING

    manager.set_state(ServiceState.STOPPED)
    assert manager.state == ServiceState.STOPPED
