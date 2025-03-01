"""Clock service router."""

from collections.abc import Callable
from typing import Any

from chronopype.clocks.modes import ClockMode
from pydantic import BaseModel

from processpype.core.models import ServiceStatus
from processpype.core.service.router import ServiceRouter


class ClockStatusResponse(BaseModel):
    """Clock status response model."""

    configured: bool
    running: bool
    mode: ClockMode | None = None
    tick_size: float | None = None
    current_time: float | None = None
    current_time_iso: str | None = None
    tick_counter: int | None = None


class ClockServiceRouter(ServiceRouter):
    """Router for clock service endpoints."""

    def __init__(
        self,
        name: str,
        get_status: Callable[[], ServiceStatus],
        get_clock_status: Callable[[], dict[str, Any]],
        start_service: Callable[[], Any],
        stop_service: Callable[[], Any],
        configure_service: Callable[[dict[str, Any]], Any],
        configure_and_start_service: Callable[[dict[str, Any]], Any],
    ):
        """Initialize the clock service router.

        Args:
            name: Service name
            get_status: Function to get service status
            get_clock_status: Function to get clock status
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
        self._get_clock_status = get_clock_status
        self._setup_clock_routes()

    def _setup_clock_routes(self) -> None:
        """Setup clock-specific routes."""

        @self.get("/status")
        async def get_clock_status() -> ClockStatusResponse:
            """Get current clock status."""
            status = self._get_clock_status()
            return ClockStatusResponse(**status)
