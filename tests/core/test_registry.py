"""Unit tests for service registry."""

import logging

from processpype.service.base import Service
from processpype.service.manager import ServiceManager
from processpype.service.registry import (
    AVAILABLE_SERVICES,
    get_available_services,
    get_service_class,
    register_service_class,
)


class _DummyManager(ServiceManager):
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


class RegistryTestService(Service):
    """A concrete service used only in registry tests."""

    from processpype.config.models import ServiceConfiguration

    configuration_class = ServiceConfiguration

    def create_manager(self) -> ServiceManager:
        return _DummyManager(logging.getLogger("test.registry"))

    def create_router(self):  # type: ignore[override]
        return None


def test_register_service_class() -> None:
    """Test that register_service_class adds the class to the registry."""
    # Clean up in case a previous run left it
    key = "registrytest"
    AVAILABLE_SERVICES.pop(key, None)

    result = register_service_class(RegistryTestService)

    assert result is RegistryTestService
    assert key in AVAILABLE_SERVICES
    assert AVAILABLE_SERVICES[key] is RegistryTestService

    # Cleanup
    AVAILABLE_SERVICES.pop(key, None)


def test_get_service_class_found() -> None:
    """Test retrieving a registered service class."""
    key = "registrytest"
    AVAILABLE_SERVICES[key] = RegistryTestService

    cls = get_service_class(key)
    assert cls is RegistryTestService

    AVAILABLE_SERVICES.pop(key, None)


def test_get_service_class_not_found() -> None:
    """Test retrieving a non-existent service class returns None."""
    assert get_service_class("nonexistent_service_xyz") is None


def test_get_available_services() -> None:
    """Test get_available_services returns the registry dict."""
    result = get_available_services()
    assert result is AVAILABLE_SERVICES
