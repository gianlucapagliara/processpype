from logging import Logger
from typing import Any

from agentspype.agency import Agency
from agentspype.agent.agent import Agent

from processpype.core.service.manager import ServiceManager


class AgentManager(ServiceManager):
    """Manager for agent operations.

    This manager handles the lifecycle of agents using the agentspype package.
    It delegates agent management to the Agency class from agentspype, which
    provides functionality for agent registration, lifecycle management, and monitoring.
    Agency is used through classmethods, not as an instance.
    """

    def __init__(
        self,
        logger: Logger,
    ):
        super().__init__(logger)
        self.logger.info("Initialized AgentManager for agent management")

    async def start(self) -> None:
        """Start the agent manager."""
        self.logger.info("Starting agent manager")
        # Agency doesn't require explicit starting

    async def stop(self) -> None:
        """Stop the agent manager."""
        self.logger.info("Stopping agent manager")
        await self.stop_all_agents()

    async def add_agents(self, agents: list[Agent]) -> None:
        """Add and start multiple agents.

        Args:
            agents: List of agent instances to add and start
        """
        for agent in agents:
            await self.add_agent(agent)

    async def add_agent(self, agent: Agent) -> None:
        """Add and start a single agent.

        Args:
            agent: Agent instance to add and start
        """
        agent_id = f"{agent.__class__.__name__}_{id(agent)}"
        self.logger.info(f"Adding agent: {agent_id}")

        # Start the agent's state machine
        agent.machine.safe_start()
        self.logger.info(f"Agent added and started: {agent_id}")

    async def stop_agent(self, agent_id: str) -> bool:
        """Stop a specific agent.

        Args:
            agent_id: ID of the agent to stop

        Returns:
            True if agent was found and stopped, False otherwise
        """
        # Find the agent in the agency by its ID
        agent = self.get_agent(agent_id)
        if not agent:
            self.logger.warning(f"Agent not found: {agent_id}")
            return False

        self.logger.info(f"Stopping agent: {agent_id}")

        # Stop the agent's state machine
        agent.machine.safe_stop()

        self.logger.info(f"Agent stop launched: {agent_id}")
        return True

    async def stop_all_agents(self) -> None:
        """Stop all managed agents."""
        agents = self.get_agents()
        self.logger.info(f"Stopping all agents ({len(agents)})")

        # Create a list of agent IDs to stop
        agent_ids = [f"{agent.__class__.__name__}_{id(agent)}" for agent in agents]

        for agent_id in agent_ids:
            await self.stop_agent(agent_id)

        self.logger.info("All agents stopped")

    def get_agents(self) -> list[Agent]:
        """Get all managed agents.

        Returns:
            List of all managed agent instances
        """
        return Agency.get_active_agents()

    def get_agent(self, agent_id: str) -> Agent | None:
        """Get a specific agent by ID.
        Since Agency doesn't provide direct lookup by ID, we need to
        iterate through all agents to find the one with the matching ID.

        Args:
            agent_id: ID of the agent to retrieve

        Returns:
            Agent instance if found, None otherwise
        """
        for agent in self.get_agents():
            if f"{agent.__class__.__name__}_{id(agent)}" == agent_id:
                return agent
        return None

    def get_agent_statuses(self) -> dict[str, Any]:
        """Get status information for all managed agents.

        Returns:
            Dictionary mapping agent IDs to their status information
        """
        statuses = {}

        for agent in self.get_agents():
            agent_id = f"{agent.__class__.__name__}_{id(agent)}"
            statuses[agent_id] = self._get_agent_status(agent)

        return statuses

    def _get_agent_status(self, agent: Agent) -> dict[str, Any]:
        """Get status information for a single agent.

        Args:
            agent: The agent to get status for

        Returns:
            Status information dictionary
        """
        return {
            "state": agent.machine.current_state.name,
            "class": agent.__class__.__name__,
            "status": agent.status.model_dump()
            if hasattr(agent.status, "model_dump")
            else str(agent.status),
        }
