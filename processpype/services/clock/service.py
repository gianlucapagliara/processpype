"""Clock service for ProcessPype.

This service provides basic clock functionality for time management in the application
by wrapping the chronopype clock implementation.
"""

from typing import Any, cast

from processpype.core.configuration.models import ServiceConfiguration
from processpype.core.models import ServiceState, ServiceStatus
from processpype.core.service import Service
from processpype.core.service.router import ServiceRouter
from processpype.services import register_service_class

from .config import ClockConfiguration
from .manager import ClockManager
from .router import ClockServiceRouter


@register_service_class
class ClockService(Service):
    """Service for clock management."""

    configuration_class = ClockConfiguration

    def create_manager(self) -> ClockManager:
        """Create the clock manager.

        Returns:
            A ClockManager instance
        """
        return ClockManager(self.logger)

    def create_router(self) -> ServiceRouter:
        """Create the service router with clock-specific endpoints.

        Returns:
            A router instance for this service
        """

        def get_status() -> ServiceStatus:
            """Get the current service status."""
            clock_manager = cast(ClockManager, self.manager)
            clock_status = clock_manager.get_clock_status()

            # Determine service state based on clock status
            if not clock_status["configured"]:
                state = ServiceState.INITIALIZED
            elif clock_status["running"]:
                state = ServiceState.RUNNING
            else:
                state = ServiceState.CONFIGURED

            return ServiceStatus(
                state=state,
                metadata=clock_status,
            )

        return ClockServiceRouter(
            name=self.name,
            get_status=get_status,
            get_clock_status=lambda: cast(
                ClockManager, self.manager
            ).get_clock_status(),
            start_service=self.start,
            stop_service=self.stop,
            configure_service=self.configure,
            configure_and_start_service=self.configure_and_start,
        )

    def configure(self, config: ServiceConfiguration | dict[str, Any]) -> None:
        """Configure the clock service.

        Args:
            config: Clock configuration
        """
        # Call parent configure to handle service configuration
        super().configure(config)

        # Convert to ClockConfiguration if needed
        clock_config = (
            ClockConfiguration.model_validate(config)
            if isinstance(config, dict)
            else ClockConfiguration.model_validate(config.model_dump())
        )

        # Configure the manager
        clock_manager = cast(ClockManager, self.manager)
        clock_manager.set_configuration(clock_config)

    def requires_configuration(self) -> bool:
        return False
