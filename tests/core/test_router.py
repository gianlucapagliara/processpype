"""Unit tests for application router."""

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from processpype.core.models import ServiceState
from processpype.core.router import ApplicationRouter
from processpype.core.service import Service
from processpype.core.service.manager import ServiceManager
from processpype.core.service.router import ServiceRouter


class MockService(Service):
    """Mock service for testing."""

    def __init__(self, state: ServiceState = ServiceState.INITIALIZED):
        super().__init__()
        self.status.state = state
        self._error = None

    def set_error(self, error: str) -> None:
        """Set service error."""
        self._error = error
        self.status.state = ServiceState.ERROR
        self.status.error = error

    def create_manager(self) -> ServiceManager:
        """Create a mock service manager."""
        return ServiceManager(logging.getLogger(f"test.service.{self.name}"))

    def create_router(self) -> ServiceRouter | None:
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
def mock_services() -> dict[str, MockService]:
    """Create mock services dictionary."""
    return {
        "service1": MockService(ServiceState.RUNNING),
        "service2": MockService(ServiceState.STOPPED),
    }


@pytest.fixture
def router(mock_services: dict[str, MockService]) -> ApplicationRouter:
    """Create test router instance."""

    async def start_service(name: str) -> None:
        if name not in mock_services:
            raise ValueError(f"Service {name} not found")
        mock_services[name].status.state = ServiceState.RUNNING

    async def stop_service(name: str) -> None:
        if name not in mock_services:
            raise ValueError(f"Service {name} not found")
        mock_services[name].status.state = ServiceState.STOPPED

    return ApplicationRouter(
        get_version=lambda: "1.0.0",
        get_state=lambda: ServiceState.RUNNING,
        get_services=lambda: mock_services,
        start_service=start_service,
        stop_service=stop_service,
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
    assert len(data) == 2
    assert "service1" in data
    assert "service2" in data
    assert data["service1"] == "MockService"
    assert data["service2"] == "MockService"


@pytest.mark.asyncio
async def test_start_service_success(client: TestClient) -> None:
    """Test successful service start."""
    response = client.post("/services/service1/start")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "started"
    assert data["service"] == "service1"


@pytest.mark.asyncio
async def test_start_service_not_found(client: TestClient) -> None:
    """Test starting non-existent service."""
    response = client.post("/services/nonexistent/start")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_stop_service_success(client: TestClient) -> None:
    """Test successful service stop."""
    response = client.post("/services/service1/stop")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "stopped"
    assert data["service"] == "service1"


@pytest.mark.asyncio
async def test_stop_service_not_found(client: TestClient) -> None:
    """Test stopping non-existent service."""
    response = client.post("/services/nonexistent/stop")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_service_operation_error(
    client: TestClient,
    mock_services: dict[str, MockService],
) -> None:
    """Test error handling during service operations."""

    # Mock service that raises an exception
    async def failing_start(name: str):
        raise Exception("Start failed")

    router = ApplicationRouter(
        get_version=lambda: "1.0.0",
        get_state=lambda: ServiceState.RUNNING,
        get_services=lambda: mock_services,
        start_service=failing_start,
        stop_service=lambda name: None,
    )

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.post("/services/service1/start")
    assert response.status_code == 500
    assert "Start failed" in response.json()["detail"]
    assert mock_services["service1"].status.state == ServiceState.ERROR
