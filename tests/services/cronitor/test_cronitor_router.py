"""Tests for the Cronitor router."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from processpype.core.models import ServiceState, ServiceStatus
from processpype.services.cronitor.router import CronitorServiceRouter


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI app for testing."""
    return FastAPI()


@pytest.fixture
def get_status() -> MagicMock:
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
def get_metrics() -> MagicMock:
    """Create a get_metrics callback for testing."""
    return MagicMock(
        return_value={
            "test_metric": 10.0,
        }
    )


@pytest.fixture
def start_service() -> AsyncMock:
    """Create a start_service callback for testing."""
    return AsyncMock()


@pytest.fixture
def stop_service() -> AsyncMock:
    """Create a stop_service callback for testing."""
    return AsyncMock()


@pytest.fixture
def configure_service() -> MagicMock:
    """Create a configure_service callback for testing."""
    return MagicMock()


@pytest.fixture
def configure_and_start_service() -> AsyncMock:
    """Create a configure_and_start_service callback for testing."""
    return AsyncMock()


@pytest.fixture
def router(
    get_status: MagicMock,
    get_metrics: MagicMock,
    start_service: AsyncMock,
    stop_service: AsyncMock,
    configure_service: MagicMock,
    configure_and_start_service: AsyncMock,
) -> CronitorServiceRouter:
    """Create a Cronitor router for testing."""
    return CronitorServiceRouter(
        name="cronitor",
        get_status=get_status,
        get_metrics=get_metrics,
        start_service=start_service,
        stop_service=stop_service,
        configure_service=configure_service,
        configure_and_start_service=configure_and_start_service,
    )


@pytest.fixture
def client(app: FastAPI, router: CronitorServiceRouter) -> TestClient:
    """Create a test client for the FastAPI app."""
    app.include_router(router)
    return TestClient(app)


def test_get_status(client: TestClient, get_status: MagicMock) -> None:
    """Test the GET /services/cronitor endpoint."""
    response = client.get("/services/cronitor")
    assert response.status_code == 200

    # The state is lowercase in the response
    response_json = response.json()
    assert response_json["state"] == "running"
    assert response_json["error"] is None
    assert response_json["metadata"] == {}
    assert response_json["is_configured"] is True

    get_status.assert_called_once()


def test_get_metrics(client: TestClient, get_metrics: MagicMock) -> None:
    """Test the GET /services/cronitor/metrics endpoint."""
    response = client.get("/services/cronitor/metrics")
    assert response.status_code == 200
    assert response.json() == {
        "test_metric": 10.0,
    }
    get_metrics.assert_called_once()


def test_start_service(client: TestClient, start_service: AsyncMock) -> None:
    """Test the POST /services/cronitor/start endpoint."""
    response = client.post("/services/cronitor/start")
    assert response.status_code == 200
    assert response.json() == {"status": "started", "service": "cronitor"}
    start_service.assert_awaited_once()


def test_stop_service(client: TestClient, stop_service: AsyncMock) -> None:
    """Test the POST /services/cronitor/stop endpoint."""
    response = client.post("/services/cronitor/stop")
    assert response.status_code == 200
    assert response.json() == {"status": "stopped", "service": "cronitor"}
    stop_service.assert_awaited_once()


def test_configure_service(client: TestClient, configure_service: MagicMock) -> None:
    """Test the POST /services/cronitor/configure endpoint."""
    config = {"enabled": True}
    response = client.post("/services/cronitor/configure", json=config)
    assert response.status_code == 200
    assert response.json() == {"status": "configured", "service": "cronitor"}
    configure_service.assert_called_once_with(config)


def test_configure_and_start_service(
    client: TestClient, configure_and_start_service: AsyncMock
) -> None:
    """Test the POST /services/cronitor/configure_and_start endpoint."""
    config = {"enabled": True}
    response = client.post("/services/cronitor/configure_and_start", json=config)
    assert response.status_code == 200
    assert response.json() == {
        "status": "configured and started",
        "service": "cronitor",
    }
    configure_and_start_service.assert_awaited_once_with(config)


def test_trigger_ping_when_running(client: TestClient, get_status: MagicMock) -> None:
    """Test the POST /services/cronitor/ping endpoint when service is running."""
    response = client.post("/services/cronitor/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "ping triggered"}


def test_trigger_ping_when_not_running(
    client: TestClient, get_status: MagicMock
) -> None:
    """Test the POST /services/cronitor/ping endpoint when service is not running."""
    # Mock the get_status to return a non-running state
    get_status.return_value = ServiceStatus(
        state=ServiceState.STOPPED,
        error=None,
        metadata={},
        is_configured=True,
    )

    response = client.post("/services/cronitor/ping")
    assert response.status_code == 400
    assert response.json() == {"detail": "Cronitor service is not running"}
