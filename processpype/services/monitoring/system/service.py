"""System monitoring service."""

from typing import TYPE_CHECKING

from processpype.core.service.router import ServiceRouter
from processpype.core.service.service import Service

from .config import SystemMonitoringConfiguration
from .manager import SystemMonitoringManager
from .router import SystemMonitoringRouter


class SystemMonitoringService(Service):
    """Service for monitoring system resources."""

    configuration_class = SystemMonitoringConfiguration

    if TYPE_CHECKING:
        manager: SystemMonitoringManager
        config: SystemMonitoringConfiguration

    def __init__(self, name: str | None = None):
        """Initialize the system monitoring service.

        Args:
            name: Optional service name override
        """
        name = name or "system-monitoring"
        super().__init__(name)

    def requires_configuration(self) -> bool:
        """Check if the service requires configuration before starting.

        Returns:
            True if configuration is required, False otherwise
        """
        return False

    def create_manager(self) -> SystemMonitoringManager:
        """Create the monitoring manager.

        Returns:
            A monitoring manager instance.
        """
        return SystemMonitoringManager(
            logger=self.logger,
        )

    def create_router(self) -> ServiceRouter:
        """Create the monitoring service router.

        Returns:
            A monitoring service router instance.
        """
        return SystemMonitoringRouter(
            name=self.name,
            get_status=lambda: self.status,
            get_metrics=lambda: self.manager.metrics,
            start_service=self.start,
            stop_service=self.stop,
            configure_service=self.configure,
            configure_and_start_service=self.configure_and_start,
        )

    async def start(self) -> None:
        """Start the monitoring service.

        This method configures the manager with the service configuration
        before starting it.
        """
        await super().start()

        # If we have a configuration, update the manager's settings
        if self.config:
            self.manager.set_interval(self.config.interval)
            self.manager.set_collection_settings(
                collect_cpu=self.config.collect_cpu,
                collect_memory=self.config.collect_memory,
                collect_disk=self.config.collect_disk,
                disk_path=self.config.disk_path,
            )
