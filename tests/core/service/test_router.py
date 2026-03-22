"""Unit tests for service router."""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from processpype.server.service_router import ServiceRouter
from processpype.service.models import ServiceState, ServiceStatus


@pytest.fixture
def status() -> ServiceStatus:
    """Create test service status."""
    return ServiceStatus(
        state=ServiceState.RUNNING,
        error=None,
        metadata={"key": "value"},
    )


@pytest.fixture
def router(status: ServiceStatus) -> ServiceRouter:
    """Create test router instance."""
    return ServiceRouter(
        name="test_service",
        get_status=lambda: status,
    )


@pytest.fixture
def client(router: ServiceRouter) -> TestClient:
    """Create test client."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_router_initialization(router: ServiceRouter) -> None:
    """Test router initialization."""
    assert router.prefix == "/services/test_service"


def test_get_status_endpoint(client: TestClient, status: ServiceStatus) -> None:
    """Test status endpoint."""
    response = client.get("/services/test_service")
    assert response.status_code == 200

    data = response.json()
    assert data["state"] == ServiceState.RUNNING.value
    assert data["error"] is None
    assert data["metadata"] == {"key": "value"}


def test_get_status_callback(status: ServiceStatus) -> None:
    """Test status callback functionality."""
    mock_get_status = Mock(return_value=status)
    router = ServiceRouter(
        name="test_service",
        get_status=mock_get_status,
    )

    # Create test client
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # Test endpoint
    client.get("/services/test_service")
    mock_get_status.assert_called_once()


# --- start / stop / configure / configure_and_start endpoint tests ---


def _make_client(
    status: ServiceStatus,
    start_service=None,
    stop_service=None,
    configure_service=None,
    configure_and_start_service=None,
) -> TestClient:
    router = ServiceRouter(
        name="test_service",
        get_status=lambda: status,
        start_service=start_service,
        stop_service=stop_service,
        configure_service=configure_service,
        configure_and_start_service=configure_and_start_service,
    )
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.mark.asyncio
async def test_start_service_success(status: ServiceStatus) -> None:
    """Test POST /start returns success."""

    async def _start():
        pass

    client = _make_client(status, start_service=_start)
    response = client.post("/services/test_service/start")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert data["service"] == "test_service"


@pytest.mark.asyncio
async def test_start_service_error(status: ServiceStatus) -> None:
    """Test POST /start returns 500 on exception."""

    async def _start():
        raise RuntimeError("start boom")

    client = _make_client(status, start_service=_start)
    response = client.post("/services/test_service/start")
    assert response.status_code == 500
    assert "start boom" in response.json()["detail"]


@pytest.mark.asyncio
async def test_stop_service_success(status: ServiceStatus) -> None:
    """Test POST /stop returns success."""

    async def _stop():
        pass

    client = _make_client(status, stop_service=_stop)
    response = client.post("/services/test_service/stop")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "stopped"
    assert data["service"] == "test_service"


@pytest.mark.asyncio
async def test_stop_service_error(status: ServiceStatus) -> None:
    """Test POST /stop returns 500 on exception."""

    async def _stop():
        raise RuntimeError("stop boom")

    client = _make_client(status, stop_service=_stop)
    response = client.post("/services/test_service/stop")
    assert response.status_code == 500
    assert "stop boom" in response.json()["detail"]


def test_configure_service_success(status: ServiceStatus) -> None:
    """Test POST /configure returns success."""
    configured_with = {}

    def _configure(cfg):
        configured_with.update(cfg)

    client = _make_client(status, configure_service=_configure)
    response = client.post(
        "/services/test_service/configure",
        json={"key": "value"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "configured"
    assert configured_with == {"key": "value"}


def test_configure_service_error(status: ServiceStatus) -> None:
    """Test POST /configure returns 500 on exception."""

    def _configure(cfg):
        raise ValueError("bad config")

    client = _make_client(status, configure_service=_configure)
    response = client.post(
        "/services/test_service/configure",
        json={"key": "value"},
    )
    assert response.status_code == 500
    assert "bad config" in response.json()["detail"]


@pytest.mark.asyncio
async def test_configure_and_start_success(status: ServiceStatus) -> None:
    """Test POST /configure_and_start returns success."""

    async def _configure_and_start(cfg):
        pass

    client = _make_client(status, configure_and_start_service=_configure_and_start)
    response = client.post(
        "/services/test_service/configure_and_start",
        json={"key": "value"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "configured and started"
    assert data["service"] == "test_service"


@pytest.mark.asyncio
async def test_configure_and_start_error(status: ServiceStatus) -> None:
    """Test POST /configure_and_start returns 500 on exception."""

    async def _configure_and_start(cfg):
        raise RuntimeError("config start boom")

    client = _make_client(status, configure_and_start_service=_configure_and_start)
    response = client.post(
        "/services/test_service/configure_and_start",
        json={"key": "value"},
    )
    assert response.status_code == 500
    assert "config start boom" in response.json()["detail"]


def test_routes_not_registered_when_callbacks_none(status: ServiceStatus) -> None:
    """Test that start/stop/configure routes are not created when callbacks are None."""
    client = _make_client(status)
    # Routes should not exist — FastAPI returns 404 for unregistered paths
    assert client.post("/services/test_service/start").status_code in (404, 405)
    assert client.post("/services/test_service/stop").status_code in (404, 405)
