"""System monitoring service."""

import asyncio

import psutil

from ...core.models import ServiceState
from ...core.service import Service


class MonitoringService(Service):
    """Service for monitoring system resources."""

    def __init__(self, name: str | None = None):
        super().__init__(name)
        self._monitor_task: asyncio.Task | None = None
        self._interval = 5.0  # seconds

    def setup_routes(self) -> None:
        super().setup_routes()

        @self._router.get("/metrics")
        async def get_metrics() -> dict[str, float]:
            """Get current system metrics."""
            return self.status.metadata

    async def _collect_metrics(self) -> dict[str, float]:
        """Collect system metrics."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }

    async def _monitor_loop(self) -> None:
        """Monitor loop for collecting metrics."""
        while True:
            try:
                metrics = await self._collect_metrics()
                self.status.metadata.update(metrics)
                self.logger.debug(
                    "Updated metrics",
                    extra={"metrics": metrics, "service_state": self.status.state},
                )
                await asyncio.sleep(self._interval)
            except Exception as e:
                self.logger.error(
                    "Error collecting metrics",
                    extra={"error": str(e), "service_state": self.status.state},
                )
                self.set_error(str(e))
                await asyncio.sleep(self._interval)

    async def start(self) -> None:
        """Start the monitoring service."""
        await super().start()
        self.logger.info(
            "Starting monitoring service", extra={"service_state": self.status.state}
        )

        try:
            self._monitor_task = asyncio.create_task(self._monitor_loop())
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

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

        self.status.state = ServiceState.STOPPED
