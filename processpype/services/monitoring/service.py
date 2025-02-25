"""System monitoring service."""

from typing import TYPE_CHECKING

from processpype.core.configuration.models import ServiceConfiguration

from ...core.service.router import ServiceRouter
from ...core.service.service import Service
from .manager import MonitoringManager
from .router import MonitoringServiceRouter


class MonitoringService(Service):
    """Service for monitoring system resources."""

    configuration_class = ServiceConfiguration

    if TYPE_CHECKING:
        manager: MonitoringManager

    def create_manager(self) -> MonitoringManager:
        """Create the monitoring manager.

        Returns:
            A monitoring manager instance.
        """
        return MonitoringManager(
            logger=self.logger,
        )

    def create_router(self) -> ServiceRouter:
        """Create the monitoring service router.

        Returns:
            A monitoring service router instance.
        """
        return MonitoringServiceRouter(
            name=self.name,
            get_status=lambda: self.status,
            get_metrics=lambda: self.manager.metrics,
            start_service=self.start,
            stop_service=self.stop,
            configure_service=self.configure,
            configure_and_start_service=self.configure_and_start,
        )
