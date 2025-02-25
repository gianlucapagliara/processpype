"""Tests for the AgentServiceRouter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Mock the agentspype imports
mock_agent = MagicMock()
mock_agent_module = MagicMock()
mock_agent_module.Agent = mock_agent

mock_agency = MagicMock()
mock_agency_module = MagicMock()
mock_agency_module.Agency = mock_agency

# Apply the mocks before importing the module under test
with patch.dict(
    "sys.modules",
    {
        "agentspype": MagicMock(),
        "agentspype.agent": MagicMock(),
        "agentspype.agent.agent": mock_agent_module,
        "agentspype.agency": mock_agency_module,
        "eventspype.subscribers": MagicMock(),
    },
):
    from processpype.services.agent.router import AgentServiceRouter


@pytest.fixture
def mock_get_agent_statuses() -> MagicMock:
    """Create a mock function for getting agent statuses."""
    return MagicMock(
        return_value={
            "agent1": {
                "state": "running",
                "class": "TestAgent",
                "status": {"memory_usage": 100},
            }
        }
    )


@pytest.fixture
def mock_stop_agent() -> AsyncMock:
    """Create a mock function for stopping an agent."""
    return AsyncMock(return_value=True)


@pytest.fixture
def mock_get_status() -> MagicMock:
    """Create a mock function for getting service status."""
    return MagicMock(
        return_value={
            "state": "running",
            "error": None,
            "metadata": {},
            "is_configured": False,
        }
    )


@pytest.fixture
def mock_start_service() -> AsyncMock:
    """Create a mock function for starting the service."""
    return AsyncMock()


@pytest.fixture
def mock_stop_service() -> AsyncMock:
    """Create a mock function for stopping the service."""
    return AsyncMock()


@pytest.fixture
def mock_configure_service() -> MagicMock:
    """Create a mock function for configuring the service."""
    return MagicMock()


@pytest.fixture
def mock_configure_and_start_service() -> AsyncMock:
    """Create a mock function for configuring and starting the service."""
    return AsyncMock()


@pytest.fixture
def router(
    mock_get_agent_statuses: MagicMock,
    mock_stop_agent: AsyncMock,
    mock_get_status: MagicMock,
    mock_start_service: AsyncMock,
    mock_stop_service: AsyncMock,
    mock_configure_service: MagicMock,
    mock_configure_and_start_service: AsyncMock,
) -> AgentServiceRouter:
    """Create a router for testing."""
    return AgentServiceRouter(
        name="test_agent_service",
        get_status=mock_get_status,
        start_service=mock_start_service,
        stop_service=mock_stop_service,
        configure_service=mock_configure_service,
        configure_and_start_service=mock_configure_and_start_service,
        get_agent_statuses=mock_get_agent_statuses,
        stop_agent=mock_stop_agent,
    )


@pytest.fixture
def app(router: AgentServiceRouter) -> FastAPI:
    """Create a FastAPI app for testing."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_get_agent_statuses(
    client: TestClient, mock_get_agent_statuses: MagicMock
) -> None:
    """Test getting agent statuses."""
    response = client.get("/services/test_agent_service/agents")
    assert response.status_code == 200
    assert response.json() == mock_get_agent_statuses.return_value
    mock_get_agent_statuses.assert_called_once()


@pytest.mark.asyncio
async def test_stop_agent(client: TestClient, mock_stop_agent: AsyncMock) -> None:
    """Test stopping an agent."""
    response = client.delete("/services/test_agent_service/agents/agent1")
    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "Agent agent1 stopped"}
    mock_stop_agent.assert_called_once_with("agent1")


@pytest.mark.asyncio
async def test_stop_agent_failure(
    client: TestClient, mock_stop_agent: AsyncMock
) -> None:
    """Test stopping an agent with failure."""
    mock_stop_agent.return_value = False
    response = client.delete("/services/test_agent_service/agents/agent1")
    assert response.status_code == 404
    assert response.json() == {"detail": "Agent agent1 not found"}
    mock_stop_agent.assert_called_once_with("agent1")


def test_get_service_status(client: TestClient, mock_get_status: MagicMock) -> None:
    """Test getting service status."""
    response = client.get("/services/test_agent_service")
    assert response.status_code == 200
    assert response.json() == mock_get_status.return_value
    mock_get_status.assert_called_once()


@pytest.mark.asyncio
async def test_start_service(client: TestClient, mock_start_service: AsyncMock) -> None:
    """Test starting the service."""
    response = client.post("/services/test_agent_service/start")
    assert response.status_code == 200
    assert response.json() == {"status": "started", "service": "test_agent_service"}
    mock_start_service.assert_called_once()


@pytest.mark.asyncio
async def test_stop_service(client: TestClient, mock_stop_service: AsyncMock) -> None:
    """Test stopping the service."""
    response = client.post("/services/test_agent_service/stop")
    assert response.status_code == 200
    assert response.json() == {"status": "stopped", "service": "test_agent_service"}
    mock_stop_service.assert_called_once()


def test_configure_service(
    client: TestClient, mock_configure_service: MagicMock
) -> None:
    """Test configuring the service."""
    config = {"agent_name": "TestAgent", "agent_path": "path/to/agent"}
    response = client.post("/services/test_agent_service/configure", json=config)
    assert response.status_code == 200
    assert response.json() == {"status": "configured", "service": "test_agent_service"}
    mock_configure_service.assert_called_once()
    # Check that the config was passed correctly
    args, _ = mock_configure_service.call_args
    assert args[0] == config


@pytest.mark.asyncio
async def test_configure_and_start_service(
    client: TestClient, mock_configure_and_start_service: AsyncMock
) -> None:
    """Test configuring and starting the service."""
    config = {"agent_name": "TestAgent", "agent_path": "path/to/agent"}
    response = client.post(
        "/services/test_agent_service/configure_and_start", json=config
    )
    assert response.status_code == 200
    assert response.json() == {
        "status": "configured and started",
        "service": "test_agent_service",
    }
    mock_configure_and_start_service.assert_called_once()
    # Check that the config was passed correctly
    args, _ = mock_configure_and_start_service.call_args
    assert args[0] == config
