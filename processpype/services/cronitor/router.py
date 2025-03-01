"""Cronitor service router."""

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException

from processpype.core.models import ServiceStatus
from processpype.core.service.router import ServiceRouter


class CronitorServiceRouter(ServiceRouter):
    """Router for Cronitor service endpoints."""

    def __init__(
        self,
        name: str,
        get_status: Callable[[], ServiceStatus],
        get_metrics: Callable[[], dict[str, float]],
        start_service: Callable[[], Any],
        stop_service: Callable[[], Any],
        configure_service: Callable[[dict[str, Any]], Any],
        configure_and_start_service: Callable[[dict[str, Any]], Any],
    ):
        """Initialize the Cronitor service router.

        Args:
            name: Service name
            get_status: Function to get service status
            get_metrics: Function to get service metrics
            start_service: Function to start the service
            stop_service: Function to stop the service
            configure_service: Function to configure the service
            configure_and_start_service: Function to configure and start the service
        """
        super().__init__(
            name=name,
            get_status=get_status,
            start_service=start_service,
            stop_service=stop_service,
            configure_service=configure_service,
            configure_and_start_service=configure_and_start_service,
        )
        self._get_metrics = get_metrics
        self._setup_cronitor_routes()

    def _setup_cronitor_routes(self) -> None:
        """Setup Cronitor-specific routes."""

        @self.get("/metrics")
        async def get_metrics_route() -> dict[str, float]:
            """Get current metrics."""
            return self._get_metrics()

        @self.post("/ping")
        async def trigger_ping() -> dict[str, str]:
            """Manually trigger a ping to Cronitor."""
            if self._get_status().state != "running":
                raise HTTPException(
                    status_code=400,
                    detail="Cronitor service is not running",
                )
            return {"status": "ping triggered"}
