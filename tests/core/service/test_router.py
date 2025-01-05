"""Unit tests for service router."""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from processpype.core.models import ServiceState, ServiceStatus
from processpype.core.service.router import ServiceRouter


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


def test_router_initialization(router: ServiceRouter):
    """Test router initialization."""
    assert router.prefix == "/services/test_service"


def test_get_status_endpoint(client: TestClient, status: ServiceStatus):
    """Test status endpoint."""
    response = client.get("/services/test_service")
    assert response.status_code == 200

    data = response.json()
    assert data["state"] == ServiceState.RUNNING.value
    assert data["error"] is None
    assert data["metadata"] == {"key": "value"}


def test_get_status_callback(status: ServiceStatus):
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
