"""Service registry — re-exports from processpype.service.registry."""

from processpype.service.registry import (
    AVAILABLE_SERVICES,
    get_available_services,
    get_service_class,
    register_service_class,
)

__all__ = [
    "AVAILABLE_SERVICES",
    "register_service_class",
    "get_available_services",
    "get_service_class",
]
