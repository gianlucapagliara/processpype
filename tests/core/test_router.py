"""Unit tests for application router."""

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from processpype.server.app_router import ApplicationRouter
from processpype.server.service_router import ServiceRouter
from processpype.service.base import Service
from processpype.service.manager import ServiceManager
from processpype.service.models import ServiceState


class MockService(Service):
    """Mock service for testing."""

    def __init__(self, state: ServiceState = ServiceState.INITIALIZED):
        """Initialize mock service.

        Args:
            state: Initial service state
        """
        super().__init__()  # Let parent class handle name generation
        self.status.state = state
        self._error: str | None = None

    def set_error(self, error: str) -> None:
        """Set service error."""
        self._error = error
        self.status.state = ServiceState.ERROR
        self.status.error = error

    def create_manager(self) -> ServiceManager:
        """Create a mock service manager."""
        logger_name = "test.service." + self.name

        class _NoOpManager(ServiceManager):
            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass

        return _NoOpManager(logging.getLogger(logger_name))

    def create_router(self) -> ServiceRouter:
        """Create a mock service router."""
        return ServiceRouter(
            name=self.name,
            get_status=lambda: self.status,
        )

    async def start(self) -> None:
        """Start the mock service."""
        await super().start()
        self.status.state = ServiceState.RUNNING

    async def stop(self) -> None:
        """Stop the mock service."""
        await super().stop()
        self.status.state = ServiceState.STOPPED


@pytest.fixture
def mock_services() -> dict[str, Service]:
    """Create mock services dictionary."""
    return {
        "service1": MockService(ServiceState.RUNNING),
        "service2": MockService(ServiceState.STOPPED),
    }


@pytest.fixture
def router(mock_services: dict[str, Service]) -> ApplicationRouter:
    """Create test router instance."""
    return ApplicationRouter(
        get_version=lambda: "1.0.0",
        get_state=lambda: ServiceState.RUNNING,
        get_services=lambda: mock_services,
    )


@pytest.fixture
def client(router: ApplicationRouter) -> TestClient:
    """Create test client."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.mark.asyncio
async def test_get_status(client: TestClient) -> None:
    """Test status endpoint."""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["version"] == "1.0.0"
    assert data["state"] == ServiceState.RUNNING.value
    assert len(data["services"]) == 2
    assert data["services"]["service1"]["state"] == ServiceState.RUNNING.value
    assert data["services"]["service2"]["state"] == ServiceState.STOPPED.value


@pytest.mark.asyncio
async def test_list_services(client: TestClient) -> None:
    """Test services listing endpoint."""
    response = client.get("/services")
    assert response.status_code == 200

    data = response.json()
    assert "services" in data
    assert len(data["services"]) == 2

    # Check that both services are in the response
    service_names = [service["name"] for service in data["services"]]
    assert "service1" in service_names
    assert "service2" in service_names


@pytest.mark.asyncio
async def test_register_service_no_app_instance(client: TestClient) -> None:
    """Test register endpoint when Application.get_instance() returns None."""
    from unittest.mock import patch

    from processpype.application import Application

    with patch.object(Application, "get_instance", return_value=None):
        response = client.post(
            "/services/register",
            json={"service_name": "foo"},
        )
    assert response.status_code == 500
    assert "not available" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_service_class_not_found(client: TestClient) -> None:
    """Test register endpoint when service class is not in the registry."""
    from unittest.mock import MagicMock, patch

    from processpype.application import Application

    mock_app = MagicMock()
    mock_app.register_service_by_name.return_value = None

    with patch.object(Application, "get_instance", return_value=mock_app):
        response = client.post(
            "/services/register",
            json={"service_name": "nonexistent"},
        )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_service_success(client: TestClient) -> None:
    """Test successful service registration via the endpoint."""
    from unittest.mock import MagicMock, patch

    from processpype.application import Application

    mock_service = MagicMock()
    mock_service.name = "my_svc"
    mock_service.__class__.__name__ = "MySvc"

    mock_app = MagicMock()
    mock_app.register_service_by_name.return_value = mock_service

    with patch.object(Application, "get_instance", return_value=mock_app):
        response = client.post(
            "/services/register",
            json={"service_name": "my_svc", "instance_name": "inst1"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "registered"
    assert data["service"] == "my_svc"


@pytest.mark.asyncio
async def test_register_service_value_error(client: TestClient) -> None:
    """Test register endpoint returns 400 on ValueError."""
    from unittest.mock import MagicMock, patch

    from processpype.application import Application

    mock_app = MagicMock()
    mock_app.register_service_by_name.side_effect = ValueError("duplicate")

    with patch.object(Application, "get_instance", return_value=mock_app):
        response = client.post(
            "/services/register",
            json={"service_name": "dup"},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_service_generic_error(client: TestClient) -> None:
    """Test register endpoint returns 500 on unexpected error."""
    from unittest.mock import MagicMock, patch

    from processpype.application import Application

    mock_app = MagicMock()
    mock_app.register_service_by_name.side_effect = RuntimeError("boom")

    with patch.object(Application, "get_instance", return_value=mock_app):
        response = client.post(
            "/services/register",
            json={"service_name": "x"},
        )
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_deregister_service_no_app_instance(client: TestClient) -> None:
    """Test deregister endpoint when Application instance is None."""
    from unittest.mock import patch

    from processpype.application import Application

    with patch.object(Application, "get_instance", return_value=None):
        response = client.delete("/services/svc1")
    assert response.status_code == 500
    assert "not available" in response.json()["detail"]


@pytest.mark.asyncio
async def test_deregister_service_success(client: TestClient) -> None:
    """Test successful service deregistration."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from processpype.application import Application

    mock_app = MagicMock()
    mock_app.deregister_service = AsyncMock(return_value=True)

    with patch.object(Application, "get_instance", return_value=mock_app):
        response = client.delete("/services/svc1")
    assert response.status_code == 200
    assert response.json()["status"] == "deregistered"


@pytest.mark.asyncio
async def test_deregister_service_failure(client: TestClient) -> None:
    """Test deregister endpoint when deregister returns False."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from processpype.application import Application

    mock_app = MagicMock()
    mock_app.deregister_service = AsyncMock(return_value=False)

    with patch.object(Application, "get_instance", return_value=mock_app):
        response = client.delete("/services/svc1")
    assert response.status_code == 500
    assert "Failed to deregister" in response.json()["detail"]


@pytest.mark.asyncio
async def test_deregister_service_value_error(client: TestClient) -> None:
    """Test deregister endpoint returns 404 on ValueError (not found)."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from processpype.application import Application

    mock_app = MagicMock()
    mock_app.deregister_service = AsyncMock(
        side_effect=ValueError("Service svc1 not found")
    )

    with patch.object(Application, "get_instance", return_value=mock_app):
        response = client.delete("/services/svc1")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deregister_service_generic_error(client: TestClient) -> None:
    """Test deregister endpoint returns 500 on unexpected error."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from processpype.application import Application

    mock_app = MagicMock()
    mock_app.deregister_service = AsyncMock(side_effect=RuntimeError("boom"))

    with patch.object(Application, "get_instance", return_value=mock_app):
        response = client.delete("/services/svc1")
    assert response.status_code == 500
