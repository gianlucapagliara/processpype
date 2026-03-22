"""Unit tests for application manager."""

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable
from unittest.mock import MagicMock

import pytest

from processpype.app_manager import ApplicationManager
from processpype.config.models import (
    AppConfig,
    ProcessPypeConfig,
    ServerConfig,
    ServiceConfiguration,
)
from processpype.server.service_router import ServiceRouter
from processpype.service.base import Service
from processpype.service.manager import ServiceManager
from processpype.service.models import ServiceState


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


class MockServiceManager(ServiceManager):
    """Mock service manager for testing."""

    def __init__(self, logger: logging.Logger):
        """Initialize mock service manager.

        Args:
            logger: Logger instance
        """
        super().__init__(logger)
        self._start_called = False
        self._stop_called = False

    @property
    def start_called(self) -> bool:
        """Check if start was called."""
        return self._start_called

    @property
    def stop_called(self) -> bool:
        """Check if stop was called."""
        return self._stop_called

    async def start(self) -> None:
        """Start the mock service manager."""
        self._start_called = True

    async def stop(self) -> None:
        """Stop the mock service manager."""
        self._stop_called = True


class MockService(Service):
    """Mock service for testing."""

    configuration_class = ServiceConfiguration

    if TYPE_CHECKING:
        manager: MockServiceManager

    def __init__(self, name: str | None = None):
        """Initialize mock service.

        Args:
            name: Optional service name
        """
        # Test tracking attributes
        self._configure_called = False
        self._config: ServiceConfiguration | None = None
        self._logger = logging.getLogger(f"test.service.{name or 'mock'}")
        super().__init__(name)

    @property
    def start_called(self) -> bool:
        """Check if start was called."""
        return self.manager.start_called

    @property
    def stop_called(self) -> bool:
        """Check if stop was called."""
        return self.manager.stop_called

    @property
    def configure_called(self) -> bool:
        """Check if configure was called."""
        return self._configure_called

    @property
    def config(self) -> ServiceConfiguration | None:
        """Get service configuration."""
        return self._config

    def configure(self, config: ServiceConfiguration | dict) -> None:
        """Configure the mock service."""
        super().configure(config)
        self._configure_called = True
        self._config = self.config

    def create_manager(self) -> MockServiceManager:
        """Create a mock service manager."""
        if self._logger is None:
            self._logger = logging.getLogger(f"test.service.{self.name or 'mock'}")
        return MockServiceManager(self._logger)

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
def app_config() -> ProcessPypeConfig:
    """Create test application configuration."""
    return ProcessPypeConfig(
        app=AppConfig(
            title="Test App",
            version="1.0.0",
            environment="testing",
            debug=True,
        ),
        server=ServerConfig(
            host="localhost",
            port=8080,
        ),
        services={
            "test_service": ServiceConfiguration(
                autostart=True,
            )
        },
    )


@pytest.fixture
def manager(
    logger: logging.Logger, app_config: ProcessPypeConfig
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
    assert service.config.autostart


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
    error_service.manager._start_called = False  # Reset the flag
    error_service.manager.start = MagicMock(side_effect=Exception("Start failed"))  # type: ignore[method-assign]
    manager._services["test_service"] = error_service

    # Should not raise exception
    await manager.start_enabled_services()


async def test_stop_all_services(manager: ApplicationManager) -> None:
    """Test stopping all services."""
    service1 = manager.register_service(MockService, name="service1")
    service2 = manager.register_service(MockService, name="service2")
    assert isinstance(service1, MockService)
    assert isinstance(service2, MockService)

    # Mark services as configured so they can be started
    service1.status.is_configured = True
    service2.status.is_configured = True

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
    error_service.manager._stop_called = False  # Reset the flag
    error_service.manager.stop = MagicMock(side_effect=Exception("Stop failed"))  # type: ignore[method-assign]
    manager._services["test_service"] = error_service

    # Should not raise exception
    await manager.stop_all_services()


def test_set_state(manager: ApplicationManager) -> None:
    """Test setting application state."""
    manager.set_state(ServiceState.RUNNING)
    assert manager.state.value == "running"

    manager.set_state(ServiceState.STOPPED)
    assert manager.state.value == "stopped"


async def test_service_registration_auto_name(manager: ApplicationManager) -> None:
    """Test automatic name generation and deduplication."""
    svc1 = manager.register_service(MockService)
    # derive_service_name strips 'service' and lowercases -> 'mock'
    assert svc1.name == "mock"

    svc2 = manager.register_service(MockService)
    assert svc2.name == "mock_1"


async def test_configure_service(manager: ApplicationManager) -> None:
    """Test configure_service delegates to the service."""
    service = manager.register_service(MockService, name="cfg_svc")
    manager.configure_service("cfg_svc", {"enabled": True})
    assert service.configure_called


async def test_configure_service_not_found(manager: ApplicationManager) -> None:
    """Test configure_service raises for nonexistent service."""
    with pytest.raises(ValueError, match="not found"):
        manager.configure_service("ghost", {})


async def test_configure_and_start_service(manager: ApplicationManager) -> None:
    """Test configure_and_start_service delegates correctly."""
    manager.register_service(MockService, name="cas_svc")
    await manager.configure_and_start_service("cas_svc", {"enabled": True})
    svc = manager.get_service("cas_svc")
    assert svc is not None
    assert svc.status.state == ServiceState.RUNNING


async def test_configure_and_start_service_not_found(
    manager: ApplicationManager,
) -> None:
    """Test configure_and_start_service raises for nonexistent service."""
    with pytest.raises(ValueError, match="not found"):
        await manager.configure_and_start_service("ghost", {})


async def test_get_services_by_type(manager: ApplicationManager) -> None:
    """Test filtering services by type."""
    manager.register_service(MockService, name="svc_a")
    manager.register_service(MockService, name="svc_b")

    results = manager.get_services_by_type(MockService)
    assert len(results) == 2


async def test_start_enabled_services_disabled_via_dict() -> None:
    """Test that services disabled via a raw dict config are skipped."""
    logger = logging.getLogger("test")
    config = ProcessPypeConfig(
        app=AppConfig(title="T", version="1.0.0", environment="testing"),
        server=ServerConfig(host="localhost", port=8080),
        services={
            "my_svc": ServiceConfiguration(enabled=False),
        },
    )
    mgr = ApplicationManager(logger, config)
    svc = mgr.register_service(MockService, name="my_svc")
    await mgr.start_enabled_services()
    # Service was disabled, so it should NOT have been started
    assert not svc.start_called


async def test_start_enabled_services_skips_unconfigured_requiring_config(
    manager: ApplicationManager,
) -> None:
    """Test that unconfigured services requiring config are not started."""
    svc = manager.register_service(MockService, name="needs_config")
    assert not svc.status.is_configured
    await manager.start_enabled_services()
    assert not svc.start_called


async def test_stop_all_services_skips_non_running() -> None:
    """Test that stop_all_services skips services not in RUNNING/STARTING state."""
    logger = logging.getLogger("test")
    config = ProcessPypeConfig(
        app=AppConfig(title="T", version="1.0.0", environment="testing"),
        server=ServerConfig(host="localhost", port=8080),
        services={},
    )
    mgr = ApplicationManager(logger, config)
    svc = mgr.register_service(MockService, name="idle")
    # Service is INITIALIZED, not RUNNING — should be skipped
    await mgr.stop_all_services()
    assert not svc.stop_called
