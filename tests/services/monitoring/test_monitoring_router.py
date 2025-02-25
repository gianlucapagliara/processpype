"""Tests for the monitoring router."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from processpype.core.models import ServiceState, ServiceStatus
from processpype.services.monitoring.router import MonitoringServiceRouter


@pytest.fixture
def app():
    """Create a FastAPI app for testing."""
    return FastAPI()


@pytest.fixture
def get_status():
    """Create a get_status callback for testing."""
    return MagicMock(
        return_value=ServiceStatus(
            state=ServiceState.RUNNING,
            error=None,
            metadata={},
            is_configured=True,
        )
    )


@pytest.fixture
def get_metrics():
    """Create a get_metrics callback for testing."""
    return MagicMock(
        return_value={
            "cpu_percent": 10.0,
            "memory_percent": 50.0,
            "disk_percent": 30.0,
        }
    )


@pytest.fixture
def start_service():
    """Create a start_service callback for testing."""
    return AsyncMock()


@pytest.fixture
def stop_service():
    """Create a stop_service callback for testing."""
    return AsyncMock()


@pytest.fixture
def configure_service():
    """Create a configure_service callback for testing."""
    return MagicMock()


@pytest.fixture
def configure_and_start_service():
    """Create a configure_and_start_service callback for testing."""
    return AsyncMock()


@pytest.fixture
def router(
    get_status,
    get_metrics,
    start_service,
    stop_service,
    configure_service,
    configure_and_start_service,
):
    """Create a monitoring router for testing."""
    return MonitoringServiceRouter(
        name="monitoring",
        get_status=get_status,
        get_metrics=get_metrics,
        start_service=start_service,
        stop_service=stop_service,
        configure_service=configure_service,
        configure_and_start_service=configure_and_start_service,
    )


@pytest.fixture
def client(app, router):
    """Create a test client for the FastAPI app."""
    app.include_router(router)
    return TestClient(app)


def test_get_status(client, get_status):
    """Test the GET /services/monitoring endpoint."""
    response = client.get("/services/monitoring")
    assert response.status_code == 200

    # The state is lowercase in the response
    response_json = response.json()
    assert response_json["state"] == "running"
    assert response_json["error"] is None
    assert response_json["metadata"] == {}
    assert response_json["is_configured"] is True

    get_status.assert_called_once()


def test_get_metrics(client, get_metrics):
    """Test the GET /services/monitoring/metrics endpoint."""
    response = client.get("/services/monitoring/metrics")
    assert response.status_code == 200
    assert response.json() == {
        "cpu_percent": 10.0,
        "memory_percent": 50.0,
        "disk_percent": 30.0,
    }
    get_metrics.assert_called_once()


def test_start_service(client, start_service):
    """Test the POST /services/monitoring/start endpoint."""
    response = client.post("/services/monitoring/start")
    assert response.status_code == 200
    assert response.json() == {"status": "started", "service": "monitoring"}
    start_service.assert_awaited_once()


def test_stop_service(client, stop_service):
    """Test the POST /services/monitoring/stop endpoint."""
    response = client.post("/services/monitoring/stop")
    assert response.status_code == 200
    assert response.json() == {"status": "stopped", "service": "monitoring"}
    stop_service.assert_awaited_once()


def test_configure_service(client, configure_service):
    """Test the POST /services/monitoring/configure endpoint."""
    config = {"enabled": True}
    response = client.post("/services/monitoring/configure", json=config)
    assert response.status_code == 200
    assert response.json() == {"status": "configured", "service": "monitoring"}
    configure_service.assert_called_once_with(config)


def test_configure_and_start_service(client, configure_and_start_service):
    """Test the POST /services/monitoring/configure_and_start endpoint."""
    config = {"enabled": True}
    response = client.post("/services/monitoring/configure_and_start", json=config)
    assert response.status_code == 200
    assert response.json() == {
        "status": "configured and started",
        "service": "monitoring",
    }
    configure_and_start_service.assert_awaited_once_with(config)
