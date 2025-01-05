"""System monitoring service."""

from typing import cast

from ...core.models import ServiceState
from ...core.service.router import ServiceRouter
from ...core.service.service import Service
from .manager import MonitoringManager
from .router import MonitoringServiceRouter


class MonitoringService(Service):
    """Service for monitoring system resources."""

    def create_manager(self) -> MonitoringManager:
        """Create the monitoring manager.

        Returns:
            A monitoring manager instance.
        """
        return MonitoringManager(self.logger)

    def create_router(self) -> ServiceRouter:
        """Create the monitoring service router.

        Returns:
            A monitoring service router instance.
        """
        return MonitoringServiceRouter(
            name=self.name,
            get_status=lambda: self.status,
            get_metrics=lambda: cast(MonitoringManager, self.manager).metrics,
        )

    async def start(self) -> None:
        """Start the monitoring service."""
        await super().start()
        self.logger.info(
            "Starting monitoring service", extra={"service_state": self.status.state}
        )

        try:
            await cast(MonitoringManager, self.manager).start_monitoring()
            self.status.state = ServiceState.RUNNING
        except Exception as e:
            error_msg = f"Failed to start monitoring: {e}"
            self.logger.error(
                error_msg, extra={"error": str(e), "service_state": self.status.state}
            )
            self.set_error(error_msg)
            raise

    async def stop(self) -> None:
        """Stop the monitoring service."""
        await super().stop()
        self.logger.info(
            "Stopping monitoring service", extra={"service_state": self.status.state}
        )

        await cast(MonitoringManager, self.manager).stop_monitoring()
        self.status.state = ServiceState.STOPPED
