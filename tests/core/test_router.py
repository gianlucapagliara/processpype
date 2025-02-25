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
        return ServiceManager(logging.getLogger(logger_name))

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
async def test_start_service_success(client: TestClient) -> None:
    """Test successful service start."""
    # Skip this test as the endpoint is no longer available in the router
    # Service operations are now handled by the Application class
    pytest.skip("Service operations are now handled by the Application class")


@pytest.mark.asyncio
async def test_start_service_not_found(client: TestClient) -> None:
    """Test starting non-existent service."""
    # Skip this test as the endpoint is no longer available in the router
    # Service operations are now handled by the Application class
    pytest.skip("Service operations are now handled by the Application class")


@pytest.mark.asyncio
async def test_stop_service_success(client: TestClient) -> None:
    """Test successful service stop."""
    # Skip this test as the endpoint is no longer available in the router
    # Service operations are now handled by the Application class
    pytest.skip("Service operations are now handled by the Application class")


@pytest.mark.asyncio
async def test_stop_service_not_found(client: TestClient) -> None:
    """Test stopping non-existent service."""
    # Skip this test as the endpoint is no longer available in the router
    # Service operations are now handled by the Application class
    pytest.skip("Service operations are now handled by the Application class")


@pytest.mark.asyncio
async def test_service_operation_error(
    client: TestClient,
    mock_services: dict[str, Service],
) -> None:
    """Test error handling during service operations."""
    # Skip this test as it's no longer applicable with the new router implementation
    # The service operations are now handled by the Application class
    pytest.skip("Service operations are now handled by the Application class")
