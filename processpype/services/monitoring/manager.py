"""System monitoring manager."""

import asyncio
import logging

import psutil

from processpype.core.service.manager import ServiceManager


class MonitoringManager(ServiceManager):
    """Manager for system monitoring operations."""

    def __init__(self, logger: logging.Logger):
        """Initialize the monitoring manager.

        Args:
            logger: Logger instance for monitoring operations
        """
        super().__init__(logger)
        self._metrics: dict[str, float] = {}
        self._monitor_task: asyncio.Task[None] | None = None
        self._interval = 5.0  # seconds

    @property
    def metrics(self) -> dict[str, float]:
        """Get current system metrics."""
        return self._metrics

    async def start_monitoring(self) -> None:
        """Start the monitoring loop."""
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitoring(self) -> None:
        """Stop the monitoring loop."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

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
                self._metrics.update(metrics)
                self.logger.debug(
                    "Updated metrics",
                    extra={"metrics": metrics},
                )
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    "Error collecting metrics",
                    extra={"error": str(e)},
                )
                await asyncio.sleep(self._interval)
