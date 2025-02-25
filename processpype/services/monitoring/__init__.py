"""Monitoring service module."""

from processpype.services import register_service_class

from .service import MonitoringService

# Register the service with the registry
register_service_class(MonitoringService)

__all__ = ["MonitoringService"]
