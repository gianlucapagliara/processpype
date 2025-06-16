"""Cronitor service."""

from typing import TYPE_CHECKING

from processpype.core.service.router import ServiceRouter
from processpype.core.service.service import Service

from .config import CronitorConfiguration
from .manager import CronitorManager
from .router import CronitorServiceRouter


class CronitorService(Service):
    """Service for sending pings to Cronitor."""

    configuration_class = CronitorConfiguration

    if TYPE_CHECKING:
        manager: CronitorManager
        config: CronitorConfiguration

    def requires_configuration(self) -> bool:
        """Check if the service requires configuration before starting.

        Returns:
            True if configuration is required, False otherwise
        """
        return True

    def create_manager(self) -> CronitorManager:
        """Create the Cronitor manager.

        Returns:
            A Cronitor manager instance.
        """
        return CronitorManager(
            logger=self.logger,
        )

    def create_router(self) -> ServiceRouter:
        """Create the Cronitor service router.

        Returns:
            A Cronitor service router instance.
        """
        return CronitorServiceRouter(
            name=self.name,
            get_status=lambda: self.status,
            get_metrics=lambda: {},  # No metrics to expose
            start_service=self.start,
            stop_service=self.stop,
            configure_service=self.configure,
            configure_and_start_service=self.configure_and_start,
        )

    async def start(self) -> None:
        """Start the Cronitor service.

        This method configures the manager with the service configuration
        before starting it.
        """
        await super().start()

        # If we have a configuration, update the manager's settings
        if self.config:
            self.manager.set_api_key(self.config.api_key)
            self.manager.set_monitor_key(self.config.monitor_key)
            self.manager.set_interval(self.config.interval)
            self.manager.set_state(self.config.state)
            self.manager.set_environment(self.config.environment)
            self.manager.set_series(self.config.series)
            self.manager.set_metrics(self.config.metrics)

    async def trigger_ping(self) -> dict[str, str]:
        """Manually trigger a ping to Cronitor.

        Returns:
            Success message
        """
        if isinstance(self.manager, CronitorManager):
            await self.manager._ping_cronitor()
            return {"status": "ping sent"}
        return {"status": "error", "message": "Manager not initialized"}
