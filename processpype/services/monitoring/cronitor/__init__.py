"""Cronitor service module."""

from processpype.services import register_service_class

from .config import CronitorConfiguration
from .service import CronitorService

# Register the service with the registry
register_service_class(CronitorService)

__all__ = ["CronitorService", "CronitorConfiguration"]
