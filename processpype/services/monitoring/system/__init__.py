"""Monitoring service module."""

from processpype.services import register_service_class

from .config import SystemMonitoringConfiguration
from .service import SystemMonitoringService

# Register the service with the registry
register_service_class(SystemMonitoringService)

__all__ = ["SystemMonitoringService", "SystemMonitoringConfiguration"]
