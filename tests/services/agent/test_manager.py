"""Tests for the AgentManager."""

import logging
from logging import Logger
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock the agentspype imports
mock_agent = MagicMock()
mock_agency = MagicMock()
mock_agency_module = MagicMock()
mock_agency_module.Agency = mock_agency

# Apply the mocks before importing the module under test
with patch.dict(
    "sys.modules",
    {
        "agentspype": MagicMock(),
        "agentspype.agent": MagicMock(),
        "agentspype.agent.agent": MagicMock(Agent=MagicMock()),
        "agentspype.agency": mock_agency_module,
        "eventspype.subscribers": MagicMock(),
    },
):
    from processpype.services.agent.manager import AgentManager


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
def logger() -> Logger:
    """Create a logger for testing."""
    return logging.getLogger("test_agent_manager")


@pytest.fixture
def agent_manager(logger: Logger) -> AgentManager:
    """Create an agent manager for testing."""
    # Set up the Agency classmethod
    mock_agency.get_active_agents = MagicMock(return_value=[])
    manager = AgentManager(logger=logger)
    return manager


@pytest.fixture
def mock_agent() -> MockAgent:
    """Create a mock agent for testing."""
    return MockAgent(config={"key": "value"})


@pytest.mark.asyncio
async def test_start_stop(agent_manager: AgentManager) -> None:
    """Test starting and stopping the agent manager."""
    # Start the manager
    await agent_manager.start()

    # Stop the manager
    with patch.object(
        agent_manager, "stop_all_agents", new_callable=AsyncMock
    ) as mock_stop_all:
        await agent_manager.stop()
        mock_stop_all.assert_called_once()


@pytest.mark.asyncio
async def test_add_agent(agent_manager: AgentManager, mock_agent: MockAgent) -> None:
    """Test adding an agent to the manager."""
    # Add an agent
    await agent_manager.add_agent(mock_agent)

    # Check that the agent was started
    mock_agent.machine.safe_start.assert_called_once()


@pytest.mark.asyncio
async def test_add_agents(agent_manager: AgentManager, mock_agent: MockAgent) -> None:
    """Test adding multiple agents to the manager."""
    # Create multiple agents
    agents = [MockAgent(config={"key": f"value{i}"}) for i in range(3)]

    # Add the agents
    with patch.object(agent_manager, "add_agent", new_callable=AsyncMock) as mock_add:
        await agent_manager.add_agents(agents)

        # Check that add_agent was called for each agent
        assert mock_add.call_count == 3
        for i, agent in enumerate(agents):
            mock_add.assert_any_call(agent)


@pytest.mark.asyncio
async def test_stop_agent(agent_manager: AgentManager, mock_agent: MockAgent) -> None:
    """Test stopping an agent."""
    # Set up the get_agent method to return our mock agent
    with patch.object(agent_manager, "get_agent", return_value=mock_agent):
        # Stop the agent
        agent_id = f"{mock_agent.__class__.__name__}_{id(mock_agent)}"
        result = await agent_manager.stop_agent(agent_id)

        # Check the result
        assert result is True

        # Check that the agent was stopped
        mock_agent.machine.safe_stop.assert_called_once()


@pytest.mark.asyncio
async def test_stop_nonexistent_agent(agent_manager: AgentManager) -> None:
    """Test stopping a nonexistent agent."""
    # Set up the get_agent method to return None
    with patch.object(agent_manager, "get_agent", return_value=None):
        # Try to stop a nonexistent agent
        result = await agent_manager.stop_agent("nonexistent_agent")

        # Check the result
        assert result is False


@pytest.mark.asyncio
async def test_stop_all_agents(agent_manager: AgentManager) -> None:
    """Test stopping all agents."""
    # Create mock agents
    agents = [MockAgent(config={"key": f"value{i}"}) for i in range(3)]

    # Set up the get_agents method to return our mock agents
    with patch.object(agent_manager, "get_agents", return_value=agents):
        # Set up the stop_agent method to return True
        with patch.object(
            agent_manager, "stop_agent", new_callable=AsyncMock
        ) as mock_stop:
            mock_stop.return_value = True
            await agent_manager.stop_all_agents()

            # Check that stop_agent was called for each agent
            assert mock_stop.call_count == 3
            for agent in agents:
                agent_id = f"{agent.__class__.__name__}_{id(agent)}"
                mock_stop.assert_any_call(agent_id)


def test_get_agents(agent_manager: AgentManager, mock_agent: MockAgent) -> None:
    """Test getting all agents."""
    # Set up the Agency classmethod to return our mock agents
    agents = [mock_agent]
    mock_agency.get_active_agents.return_value = agents

    # Get all agents
    result = agent_manager.get_agents()

    # Check the result
    assert result == agents
    mock_agency.get_active_agents.assert_called_once()


def test_get_agent(agent_manager: AgentManager, mock_agent: MockAgent) -> None:
    """Test getting a specific agent."""
    # Set up the get_agents method to return our mock agent
    with patch.object(agent_manager, "get_agents", return_value=[mock_agent]):
        # Get the agent
        agent_id = f"{mock_agent.__class__.__name__}_{id(mock_agent)}"
        agent = agent_manager.get_agent(agent_id)

        # Check the result
        assert agent == mock_agent

    # Try to get a nonexistent agent
    with patch.object(agent_manager, "get_agents", return_value=[]):
        agent = agent_manager.get_agent("nonexistent_agent")

        # Check the result
        assert agent is None


def test_get_agent_statuses(agent_manager: AgentManager, mock_agent: MockAgent) -> None:
    """Test getting agent statuses."""
    # Set up the get_agents method to return our mock agent
    with patch.object(agent_manager, "get_agents", return_value=[mock_agent]):
        # Get agent statuses
        statuses = agent_manager.get_agent_statuses()

        # Check the result
        agent_id = f"{mock_agent.__class__.__name__}_{id(mock_agent)}"
        assert len(statuses) == 1
        assert agent_id in statuses
        assert statuses[agent_id]["state"] == "idle"
        assert statuses[agent_id]["class"] == "MockAgent"
        assert statuses[agent_id]["status"] == {"status": "ok"}
