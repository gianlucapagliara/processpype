"""Service package for ProcessPype.

This package contains all built-in services for the ProcessPype application.
Services can be registered with the application and provide specific functionality.

With the new service management approach, multiple instances of the same service
can be registered with different names, and each service manages its own lifecycle
through exposed REST endpoints.
"""

from processpype.core.service import Service

# Dictionary to track all available service classes
AVAILABLE_SERVICES: dict[str, type[Service]] = {}


def register_service_class(service_class: type[Service]) -> type[Service]:
    """Register a service class to make it available for the application.

    This is a decorator that can be used to register service classes:

    @register_service_class
    class MyService(Service):
        ...

    Args:
        service_class: The service class to register

    Returns:
        The service class (unchanged)
    """
    service_name = service_class.__name__.lower().replace("service", "")
    AVAILABLE_SERVICES[service_name] = service_class
    return service_class


def get_available_services() -> dict[str, type[Service]]:
    """Get all available service classes.

    Returns:
        Dictionary mapping service names to their classes
    """
    return AVAILABLE_SERVICES


def get_service_class(name: str) -> type[Service] | None:
    """Get a service class by name.

    Args:
        name: Service class name (without 'service' suffix)

    Returns:
        Service class or None if not found
    """
    return AVAILABLE_SERVICES.get(name)


# Import all services to ensure they get registered
from processpype.services.agent import AgentService  # noqa
from processpype.services.database import DatabaseService  # noqa
from processpype.services.monitoring import MonitoringService  # noqa
from processpype.services.notification import NotificationService  # noqa
from processpype.services.storage import StorageService  # noqa

# Export all service classes
__all__ = [
    "register_service_class",
    "get_available_services",
    "get_service_class",
    "AgentService",
    "DatabaseService",
    "MonitoringService",
    "NotificationService",
    "StorageService",
]
