"""Tests for clock service router."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from chronopype.clocks.modes import ClockMode
from fastapi import FastAPI
from fastapi.testclient import TestClient

from processpype.core.models import ServiceState, ServiceStatus
from processpype.services.clock.router import ClockServiceRouter, ClockStatusResponse


@pytest.fixture
def mock_callbacks():
    """Create mock callbacks for router testing."""
    return {
        "get_status": MagicMock(return_value=ServiceStatus(state=ServiceState.RUNNING)),
        "get_clock_status": MagicMock(
            return_value={
                "configured": True,
                "running": True,
                "mode": ClockMode.REALTIME,
                "tick_size": 1.0,
                "current_time": 1000.0,
                "current_time_iso": "2024-01-01T00:00:00",
                "tick_counter": 100,
            }
        ),
        "start_service": AsyncMock(),
        "stop_service": AsyncMock(),
        "configure_service": AsyncMock(),
        "configure_and_start_service": AsyncMock(),
    }


@pytest.fixture
def router(mock_callbacks):
    """Create a router instance for testing."""
    return ClockServiceRouter(
        name="clock",
        get_status=mock_callbacks["get_status"],
        get_clock_status=mock_callbacks["get_clock_status"],
        start_service=mock_callbacks["start_service"],
        stop_service=mock_callbacks["stop_service"],
        configure_service=mock_callbacks["configure_service"],
        configure_and_start_service=mock_callbacks["configure_and_start_service"],
    )


@pytest.fixture
def app(router):
    """Create a FastAPI app with the router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


def test_get_clock_status(client, mock_callbacks):
    """Test getting clock status."""
    response = client.get("/services/clock/status")
    assert response.status_code == 200

    status = ClockStatusResponse(**response.json())
    assert status.configured is True
    assert status.running is True
    assert status.mode == ClockMode.REALTIME
    assert status.tick_size == 1.0
    assert status.current_time == 1000.0
    assert status.current_time_iso == "2024-01-01T00:00:00"
    assert status.tick_counter == 100

    mock_callbacks["get_clock_status"].assert_called_once()


def test_get_clock_status_not_configured(client, mock_callbacks):
    """Test getting clock status when not configured."""
    mock_callbacks["get_clock_status"].return_value = {
        "configured": False,
        "running": False,
    }

    response = client.get("/services/clock/status")
    assert response.status_code == 200

    status = ClockStatusResponse(**response.json())
    assert status.configured is False
    assert status.running is False
    assert status.mode is None
    assert status.tick_size is None
    assert status.current_time is None
    assert status.current_time_iso is None
    assert status.tick_counter is None
