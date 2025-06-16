"""Router for the Monitoring service."""

from collections.abc import Callable
from typing import Any

from processpype.core.models import ServiceStatus
from processpype.core.service.router import ServiceRouter


class SystemMonitoringRouter(ServiceRouter):
    """Router for monitoring service endpoints."""

    def __init__(
        self,
        name: str,
        get_status: Callable[[], ServiceStatus],
        get_metrics: Callable[[], dict[str, float]],
        start_service: Callable[[], Any] | None = None,
        stop_service: Callable[[], Any] | None = None,
        configure_service: Callable[[dict[str, Any]], Any] | None = None,
        configure_and_start_service: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        """Initialize the monitoring service router.

        Args:
            name: Service name for route prefix
            get_status: Callback to retrieve service status
            get_metrics: Callback to get current metrics
            start_service: Callback to start the service
            stop_service: Callback to stop the service
            configure_service: Callback to configure the service
            configure_and_start_service: Callback to configure and start the service
        """
        super().__init__(
            name=name,
            get_status=get_status,
            start_service=start_service,
            stop_service=stop_service,
            configure_service=configure_service,
            configure_and_start_service=configure_and_start_service,
        )
        self._setup_monitoring_routes(
            get_metrics=get_metrics,
        )

    def _setup_monitoring_routes(
        self, get_metrics: Callable[[], dict[str, float]]
    ) -> None:
        """Setup monitoring-specific routes."""

        @self.get("/metrics")
        async def get_metrics_route() -> dict[str, float]:
            """Get current system metrics."""
            return get_metrics()
