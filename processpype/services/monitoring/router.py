"""Router for the Monitoring service."""

from collections.abc import Callable

from processpype.core.models import ServiceStatus
from processpype.core.service.router import ServiceRouter


class MonitoringServiceRouter(ServiceRouter):
    """Router for monitoring service endpoints."""

    def __init__(
        self,
        name: str,
        get_status: Callable[[], ServiceStatus],
        get_metrics: Callable[[], dict[str, float]],
    ) -> None:
        """Initialize the monitoring service router.

        Args:
            name: Service name for route prefix
            get_status: Callback to retrieve service status
            get_metrics: Callback to get current metrics
        """
        super().__init__(name, get_status)
        self._setup_monitoring_routes(get_metrics)

    def _setup_monitoring_routes(
        self, get_metrics: Callable[[], dict[str, float]]
    ) -> None:
        """Setup monitoring-specific routes."""

        @self.get("/metrics")
        async def get_metrics_route() -> dict[str, float]:
            """Get current system metrics."""
            return get_metrics()
