"""Tests for the clock service."""

from unittest.mock import patch

import pytest
from chronopype.clocks.modes import ClockMode
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from processpype.core.models import ServiceState, ServiceStatus
from processpype.services.clock.config import ClockConfiguration
from processpype.services.clock.manager import ClockManager
from processpype.services.clock.service import ClockService


@pytest.fixture
def service() -> ClockService:
    """Create a clock service instance for testing."""
    return ClockService()


@pytest.fixture
def app(service: ClockService) -> FastAPI:
    """Create a FastAPI app with the clock service router."""
    app = FastAPI()
    app.include_router(service.create_router())
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_service_creation(service: ClockService) -> None:
    """Test that the service is created correctly."""
    assert isinstance(service, ClockService)


def test_manager_creation(service: ClockService) -> None:
    """Test that the manager is created correctly."""
    assert isinstance(service.manager, ClockManager)


def test_router_creation(app: FastAPI) -> None:
    """Test that the router is created with the status endpoint."""
    # Get all routes and check if our endpoint is included
    status_routes = [
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path == "/services/clock"
    ]
    assert len(status_routes) == 1


def test_configure_service(service: ClockService) -> None:
    """Test that the service can be configured."""
    config = ClockConfiguration(mode=ClockMode.REALTIME, tick_size=1.0)
    service.configure(config)
    assert isinstance(service.manager, ClockManager)


@pytest.mark.asyncio
async def test_status_endpoint(client: TestClient, service: ClockService) -> None:
    """Test the status endpoint of the service."""
    # Mock the manager's get_clock_status method
    mock_status = {
        "configured": True,
        "running": True,
        "mode": ClockMode.REALTIME,
        "tick_size": 1.0,
        "current_time": 1000.0,
        "current_time_iso": "2024-01-01T00:00:00",
        "tick_counter": 100,
    }
    with patch.object(
        ClockManager, "get_clock_status", return_value=mock_status, autospec=True
    ):
        response = client.get("/services/clock")
        assert response.status_code == 200
        status = ServiceStatus.model_validate(response.json())
        assert status.state == ServiceState.RUNNING

        # Convert mode back to enum for comparison
        metadata = status.metadata
        if "mode" in metadata:
            metadata["mode"] = ClockMode(metadata["mode"])
        assert metadata == mock_status


@pytest.mark.asyncio
async def test_service_configuration(service: ClockService) -> None:
    """Test service configuration."""
    config = {
        "enabled": True,
        "autostart": False,
        "mode": ClockMode.REALTIME,
        "tick_size": 1.0,
    }

    # Configure the service
    service.configure(config)

    # Check that the manager was configured
    manager = service.manager
    assert isinstance(manager, ClockManager)
    assert manager._config is not None
    assert manager._config.clock_mode == ClockMode.REALTIME
    assert manager._config.tick_size == 1.0


@pytest.mark.asyncio
async def test_service_status_endpoint(service: ClockService) -> None:
    """Test the status endpoint."""
    config = {
        "enabled": True,
        "autostart": False,
        "mode": ClockMode.REALTIME,
        "tick_size": 1.0,
    }

    # Configure the service
    service.configure(config)

    # Get the status endpoint handler
    router = service.create_router()
    status_routes = [
        route
        for route in router.routes
        if isinstance(route, APIRoute) and route.path == "/services/clock"
    ]
    assert len(status_routes) == 1

    # Mock the manager's get_clock_status method
    mock_status = {
        "configured": True,
        "running": True,
        "mode": ClockMode.REALTIME,
        "tick_size": 1.0,
        "current_time": 1000.0,
        "current_time_iso": "2024-01-01T00:00:00",
        "tick_counter": 100,
    }
    with patch.object(
        ClockManager, "get_clock_status", return_value=mock_status, autospec=True
    ):
        # Call the endpoint handler directly
        response = await status_routes[0].endpoint()
        assert isinstance(response, ServiceStatus)
        assert response.state == ServiceState.RUNNING

        # Convert mode back to enum for comparison
        metadata = response.metadata
        if "mode" in metadata:
            metadata["mode"] = ClockMode(metadata["mode"])
        assert metadata == mock_status
