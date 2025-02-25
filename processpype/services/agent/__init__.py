"""Agent service module."""

from processpype.services import register_service_class

from .service import AgentService

# Register the service with the registry
register_service_class(AgentService)

__all__ = ["AgentService"]
