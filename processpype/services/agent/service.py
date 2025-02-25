from typing import TYPE_CHECKING, Any

# Import from agentspype
from processpype.core.service.service import Service
from processpype.services.agent.configuration import AgentServiceConfiguration
from processpype.services.agent.manager import AgentManager
from processpype.services.agent.router import AgentServiceRouter


class AgentService(Service):
    """Service for agent operations.

    This service manages the lifecycle of agents using the agentspype package.
    It provides functionality to:
    - Create and start agent instances
    - Monitor agent status
    - Stop agents

    Note: Agent classes should be registered elsewhere before using this service.
    """

    configuration_class = AgentServiceConfiguration

    if TYPE_CHECKING:
        manager: AgentManager
        config: AgentServiceConfiguration

    def create_manager(self) -> AgentManager:
        """Create the agent manager.

        Returns:
            An agent manager instance.
        """
        return AgentManager(
            logger=self.logger,
        )

    def create_router(self) -> AgentServiceRouter:
        """Create the agent service router.

        Returns:
            An agent service router instance.
        """
        return AgentServiceRouter(
            name=self.name,
            get_status=lambda: self.status,
            start_service=self.start,
            stop_service=self.stop,
            configure_service=self.configure,
            configure_and_start_service=self.configure_and_start,
            get_agent_statuses=self.get_agent_statuses,
            stop_agent=self.stop_agent,
        )

    async def start(self) -> None:
        """Start the agent service.

        This method:
        1. Starts the agent manager
        2. Creates and starts agent instances from configuration

        Note: Agent classes should already be registered before starting this service.
        """
        await super().start()

        # Create and start agent instances from configuration
        if self.config:
            agents = self.config.get_agent_instances()
            if agents:
                await self.manager.add_agents(agents)
                self.logger.info(f"Started {len(agents)} agents")

    async def stop(self) -> None:
        """Stop the agent service.

        This method stops all running agents and then stops the agent manager.
        """
        # Stop all agents
        await self.manager.stop_all_agents()

        # Stop the manager
        await super().stop()

    def get_agent_statuses(self) -> dict[str, Any]:
        """Get status information for all managed agents.

        Returns:
            Dictionary mapping agent IDs to their status information
        """
        return self.manager.get_agent_statuses()

    async def stop_agent(self, agent_id: str) -> bool:
        """Stop a specific agent.

        Args:
            agent_id: The ID of the agent to stop.

        Returns:
            True if the agent was stopped, False otherwise.
        """
        return await self.manager.stop_agent(agent_id)
