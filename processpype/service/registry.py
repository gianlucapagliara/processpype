"""Service class registry for ProcessPype."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import Service

# Dictionary to track all available service classes
AVAILABLE_SERVICES: dict[str, type[Service]] = {}


def register_service_class(service_class: type[Service]) -> type[Service]:
    """Decorator to register a service class.

    Usage::

        @register_service_class
        class MyService(Service):
            ...
    """
    service_name = service_class.__name__.lower().replace("service", "")
    AVAILABLE_SERVICES[service_name] = service_class
    return service_class


def get_available_services() -> dict[str, type[Service]]:
    """Get all registered service classes."""
    return AVAILABLE_SERVICES


def get_service_class(name: str) -> type[Service] | None:
    """Look up a service class by name."""
    return AVAILABLE_SERVICES.get(name)
