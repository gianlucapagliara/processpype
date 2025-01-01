"""Tests for Application class."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from processpype.core.application import Application
from processpype.core.models import ServiceState
from processpype.core.service import Service


class MockService(Service):
    """Test service implementation."""

    async def start(self) -> None:
        """Start the service."""
        await super().start()
        self.status.state = ServiceState.RUNNING

    async def stop(self) -> None:
        """Stop the service."""
        await super().stop()
        self.status.state = ServiceState.STOPPED


@pytest.mark.asyncio
async def test_application_creation():
    """Test application creation with factory method."""
    app = await Application.create(title="Test App", port=9000, environment="testing")
    assert app._config.title == "Test App"
    assert app._config.port == 9000
    assert app._config.environment == "testing"


@pytest.mark.asyncio
async def test_application_initialization(default_config):
    """Test application initialization."""
    app = Application(default_config)
    await app.initialize()

    assert isinstance(app.api, FastAPI)
    assert app.api.title == default_config.title
    assert app._setup_complete is True


@pytest.mark.asyncio
async def test_multiple_applications(default_config):
    """Test creating multiple application instances."""
    app1 = Application(default_config)
    app2 = Application(default_config)

    await app1.initialize()
    await app2.initialize()

    # Each app should have its own state
    assert app1 is not app2
    assert id(app1._services) != id(
        app2._services
    )  # Check for different dictionary instances

    # Register services in each app
    service1 = app1.register_service(MockService, name="test")
    service2 = app2.register_service(MockService, name="test")

    # Services should be independent
    assert service1 is not service2
    assert app1._services["test"] is not app2._services["test"]

    # Start service in app1 only
    await app1.start_service("test")
    assert service1.status.state == ServiceState.RUNNING
    assert service2.status.state == ServiceState.INITIALIZED

    # Each app should have its own FastAPI instance
    assert app1.api is not app2.api


@pytest.mark.asyncio
async def test_service_registration(default_config):
    """Test service registration."""
    app = Application(default_config)
    await app.initialize()

    service = app.register_service(MockService)
    assert service.name in app._services
    assert app._services[service.name] is service


@pytest.mark.asyncio
async def test_service_configuration(default_config):
    """Test service configuration during registration."""
    # Add service configuration
    default_config.services["test"] = {
        "enabled": True,
        "autostart": True,
        "metadata": {"test": "value"},
    }

    app = Application(default_config)
    await app.initialize()

    service = app.register_service(MockService, name="test")
    assert service._config is not None
    assert service._config.enabled is True
    assert service.status.metadata["test"] == "value"


@pytest.mark.asyncio
async def test_service_lifecycle(default_config):
    """Test service lifecycle management."""
    app = Application(default_config)
    await app.initialize()

    service = app.register_service(MockService)

    # Test service start
    await app.start_service(service.name)
    assert service.status.state == ServiceState.RUNNING

    # Test service stop
    await app.stop()
    assert service.status.state == ServiceState.STOPPED


@pytest.mark.asyncio
async def test_api_endpoints(default_config):
    """Test API endpoints."""
    app = Application(default_config)
    await app.initialize()

    client = TestClient(app.api)

    # Test status endpoint
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == default_config.version

    # Test services endpoint
    response = client.get("/services")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_application_context_manager(default_config):
    """Test application as async context manager."""
    async with Application(default_config) as app:
        assert app._setup_complete is True
        assert isinstance(app.api, FastAPI)

        service = app.register_service(MockService)
        assert service.name in app._services


@pytest.mark.asyncio
async def test_error_handling(default_config):
    """Test error handling during operations."""
    app = Application(default_config)

    # Test operations before initialization
    with pytest.raises(RuntimeError):
        app.register_service(MockService)

    with pytest.raises(RuntimeError):
        await app.start_service("test")

    # Test invalid service operations
    await app.initialize()
    with pytest.raises(ValueError):
        await app.start_service("nonexistent")


@pytest.mark.asyncio
async def test_service_duplicate_registration(default_config):
    """Test handling of duplicate service registration."""
    app = Application(default_config)
    await app.initialize()

    # Register first service
    service1 = app.register_service(MockService, name="test")
    assert service1.name in app._services

    # Attempt to register duplicate
    with pytest.raises(ValueError):
        app.register_service(MockService, name="test")


@pytest.mark.asyncio
async def test_application_cleanup(default_config):
    """Test proper cleanup during application stop."""
    app = Application(default_config)
    await app.initialize()

    # Register multiple services
    service1 = app.register_service(MockService, name="service1")
    service2 = app.register_service(MockService, name="service2")

    # Start services
    await app.start_service("service1")
    await app.start_service("service2")

    # Stop application
    await app.stop()

    # Verify all services are stopped
    assert service1.status.state == ServiceState.STOPPED
    assert service2.status.state == ServiceState.STOPPED
    assert app._state == ServiceState.STOPPED
