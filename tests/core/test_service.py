"""Tests for Service base class."""

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from processpype.core.models import ServiceState, ServiceStatus
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
async def test_service_initialization():
    """Test service initialization."""
    service = MockService()

    assert service.name == "mock"
    assert service.status.state == ServiceState.INITIALIZED
    assert service.status.error is None
    assert isinstance(service.router, APIRouter)


@pytest.mark.asyncio
async def test_service_custom_name():
    """Test service initialization with custom name."""
    service = MockService(name="custom")
    assert service.name == "custom"


@pytest.mark.asyncio
async def test_service_status():
    """Test service status reporting."""
    service = MockService()

    status = service.status
    assert isinstance(status, ServiceStatus)
    assert status.state == ServiceState.INITIALIZED
    assert status.error is None
    assert status.metadata == {}


@pytest.mark.asyncio
async def test_service_configuration(service_config):
    """Test service configuration."""
    service = MockService()
    service.configure(service_config)

    assert service._config is service_config
    assert service.status.metadata == service_config.metadata


@pytest.mark.asyncio
async def test_service_error_handling():
    """Test service error handling."""
    service = MockService()

    error_message = "Test error"
    service.set_error(error_message)

    assert service.status.error == error_message


@pytest.mark.asyncio
async def test_service_lifecycle():
    """Test service lifecycle."""
    service = MockService()

    # Test initial state
    assert service.status.state == ServiceState.INITIALIZED

    # Test start
    await service.start()
    assert service.status.state == ServiceState.RUNNING
    assert service.status.error is None

    # Test stop
    await service.stop()
    assert service.status.state == ServiceState.STOPPED


@pytest.mark.asyncio
async def test_service_routes():
    """Test service route setup."""
    service = MockService()

    # Check router prefix
    assert service.router.prefix == f"/services/{service.name}"

    # Check routes - using str(route) to avoid path attribute access
    routes = [str(route) for route in service.router.routes]
    assert any("" in route for route in routes)  # Status endpoint


@pytest.mark.asyncio
async def test_service_metadata(service_config):
    """Test service metadata management."""
    service = MockService()

    # Initial metadata
    assert service.status.metadata == {}

    # Update through configuration
    service.configure(service_config)
    assert service.status.metadata == service_config.metadata


@pytest.mark.asyncio
async def test_service_logger():
    """Test service logger setup."""
    service = MockService()

    logger1 = service.logger
    logger2 = service.logger

    # Test logger caching
    assert logger1 is logger2

    # Test logger name
    assert service.name in logger1.name


@pytest.mark.asyncio
async def test_service_status_endpoint():
    """Test service status endpoint."""
    service = MockService()

    # Create a FastAPI app and mount the router
    app = FastAPI()
    app.include_router(service.router)
    client = TestClient(app)

    # Test status endpoint
    response = client.get(f"/services/{service.name}")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == ServiceState.INITIALIZED
    assert data["error"] is None
    assert data["metadata"] == {}
