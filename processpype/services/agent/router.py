from collections.abc import Callable
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel

from processpype.core.models import ServiceStatus
from processpype.core.service.router import ServiceRouter


class AgentCreateRequest(BaseModel):
    """Request model for creating an agent."""

    agent_name: str
    agent_config: dict[str, Any] = {}


class AgentServiceRouter(ServiceRouter):
    """Router for agent operations.

    This router extends the base ServiceRouter with endpoints specific to agent management:
    - GET /agents - List all agents and their status
    - DELETE /agents/{agent_id} - Stop a specific agent
    - POST /agents - Create a new agent
    """

    def __init__(
        self,
        name: str,
        get_status: Callable[[], ServiceStatus],
        start_service: Callable[[], Any] | None = None,
        stop_service: Callable[[], Any] | None = None,
        configure_service: Callable[[dict[str, Any]], Any] | None = None,
        configure_and_start_service: Callable[[dict[str, Any]], Any] | None = None,
        get_agent_statuses: Callable[[], dict[str, Any]] | None = None,
        stop_agent: Callable[[str], Any] | None = None,
    ) -> None:
        """Initialize the agent service router.

        Args:
            name: Service name for route prefix
            get_status: Callback to retrieve service status
            start_service: Callback to start the service
            stop_service: Callback to stop the service
            configure_service: Callback to configure the service
            configure_and_start_service: Callback to configure and start the service
            get_agent_statuses: Callback to get status of all agents
            stop_agent: Callback to stop a specific agent
        """
        super().__init__(
            name=name,
            get_status=get_status,
            start_service=start_service,
            stop_service=stop_service,
            configure_service=configure_service,
            configure_and_start_service=configure_and_start_service,
        )

        self._get_agent_statuses = get_agent_statuses
        self._stop_agent = stop_agent

        self._setup_agent_routes()

    def _setup_agent_routes(self) -> None:
        """Setup agent-specific routes."""
        if not self._get_agent_statuses or not self._stop_agent:
            return

        @self.get("/agents")
        async def get_agents() -> dict[str, Any]:
            """Get status of all agents."""
            if not self._get_agent_statuses:
                raise HTTPException(
                    status_code=501, detail="Agent status retrieval not implemented"
                )
            return self._get_agent_statuses()

        @self.delete("/agents/{agent_id}")
        async def stop_agent(agent_id: str) -> dict[str, Any]:
            """Stop a specific agent."""
            if not self._stop_agent:
                raise HTTPException(
                    status_code=501, detail="Agent stopping not implemented"
                )

            success = await self._stop_agent(agent_id)
            if not success:
                raise HTTPException(
                    status_code=404, detail=f"Agent {agent_id} not found"
                )

            return {"success": True, "message": f"Agent {agent_id} stopped"}
