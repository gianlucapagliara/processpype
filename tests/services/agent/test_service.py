"""Tests for the AgentService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
    from processpype.services.agent.configuration import AgentServiceConfiguration
    from processpype.services.agent.manager import AgentManager
    from processpype.services.agent.service import AgentService


class MockAgent:
    """Mock agent class for testing."""

    def __init__(self, config=None):
        self.config = config
        self.machine = MagicMock()
        self.machine.safe_start = MagicMock()
        self.machine.safe_stop = MagicMock()
        self.machine.current_state = MagicMock()
        self.machine.current_state.name = "idle"
        self.status = MagicMock()
        self.status.model_dump = MagicMock(return_value={"status": "ok"})


@pytest.fixture
def mock_config() -> MagicMock:
    """Create a mock configuration for testing."""
    config = MagicMock(spec=AgentServiceConfiguration)
    config.get_agent_instances = MagicMock(return_value=[MockAgent()])
    return config


@pytest.fixture
def mock_manager() -> MagicMock:
    """Create a mock manager for testing."""
    manager = MagicMock(spec=AgentManager)
    manager.start = AsyncMock()
    manager.stop = AsyncMock()
    manager.add_agent = AsyncMock()
    manager.add_agents = AsyncMock()
    manager.stop_agent = AsyncMock(return_value=True)
    manager.get_agent_statuses = MagicMock(return_value={"agent1": {"state": "idle"}})
    return manager


@pytest.fixture
def agent_service(mock_config: MagicMock, mock_manager: MagicMock) -> AgentService:
    """Create an agent service for testing."""
    with patch(
        "processpype.services.agent.service.AgentManager", return_value=mock_manager
    ):
        service = AgentService(name="test_agent_service")
        # Manually set the config
        service._config = mock_config
        # Set the service as configured to avoid ConfigurationError
        service.status.is_configured = True
        # Manually set the manager to ensure it's the mock
        service._manager = mock_manager
        return service


@pytest.mark.asyncio
async def test_start_stop(agent_service: AgentService, mock_manager: MagicMock) -> None:
    """Test starting and stopping the agent service."""
    # Start the service
    await agent_service.start()
    mock_manager.start.assert_called_once()
    mock_manager.add_agents.assert_called_once()

    # Stop the service
    await agent_service.stop()
    mock_manager.stop.assert_called_once()


@pytest.mark.asyncio
async def test_stop_agent(agent_service: AgentService, mock_manager: MagicMock) -> None:
    """Test stopping an agent."""
    # Configure the mock to return True for the specific agent ID
    mock_manager.stop_agent.return_value = True

    # Stop an agent
    result = await agent_service.stop_agent("agent1")

    # Check the result
    assert result is True
    mock_manager.stop_agent.assert_called_once_with("agent1")


def test_get_agent_statuses(
    agent_service: AgentService, mock_manager: MagicMock
) -> None:
    """Test getting agent statuses."""
    # Set up the mock to return the expected value
    expected_statuses = {"agent1": {"state": "idle"}}
    mock_manager.get_agent_statuses.return_value = expected_statuses

    # Get agent statuses
    statuses = agent_service.get_agent_statuses()

    # Check the result
    assert statuses == expected_statuses
    mock_manager.get_agent_statuses.assert_called_once()
