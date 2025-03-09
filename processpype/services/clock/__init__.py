"""Clock service package for ProcessPype."""

from processpype.services import register_service_class

from .config import ClockConfiguration
from .manager import ClockManager
from .service import ClockService

# Register the service with the registry
register_service_class(ClockService)

__all__ = ["ClockService", "ClockManager", "ClockConfiguration"]
