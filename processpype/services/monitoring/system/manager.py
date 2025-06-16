"""System monitoring manager."""

import asyncio
import logging

import psutil

from processpype.core.service.manager import ServiceManager


class SystemMonitoringManager(ServiceManager):
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

        # Collection settings
        self._collect_cpu = True
        self._collect_memory = True
        self._collect_disk = True
        self._disk_path = "/"

    @property
    def metrics(self) -> dict[str, float]:
        """Get current system metrics."""
        return self._metrics

    def set_interval(self, interval: float) -> None:
        """Set the monitoring interval.

        Args:
            interval: Interval in seconds between metric collections
        """
        self._interval = interval
        self.logger.debug(
            "Updated monitoring interval",
            extra={"interval": interval},
        )

    def set_collection_settings(
        self,
        collect_cpu: bool = True,
        collect_memory: bool = True,
        collect_disk: bool = True,
        disk_path: str = "/",
    ) -> None:
        """Set the metric collection settings.

        Args:
            collect_cpu: Whether to collect CPU metrics
            collect_memory: Whether to collect memory metrics
            collect_disk: Whether to collect disk metrics
            disk_path: Path to monitor for disk usage
        """
        self._collect_cpu = collect_cpu
        self._collect_memory = collect_memory
        self._collect_disk = collect_disk
        self._disk_path = disk_path
        self.logger.debug(
            "Updated collection settings",
            extra={
                "collect_cpu": collect_cpu,
                "collect_memory": collect_memory,
                "collect_disk": collect_disk,
                "disk_path": disk_path,
            },
        )

    async def start(self) -> None:
        """Start the monitoring manager."""
        await self.start_monitoring()

    async def stop(self) -> None:
        """Stop the monitoring manager."""
        await self.stop_monitoring()

    async def start_monitoring(self) -> None:
        """Start the monitoring loop."""
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self.logger.info("Started monitoring loop")

    async def stop_monitoring(self) -> None:
        """Stop the monitoring loop."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
            self.logger.info("Stopped monitoring loop")

    async def _collect_metrics(self) -> dict[str, float]:
        """Collect system metrics.

        Returns:
            A dictionary of collected metrics
        """
        metrics: dict[str, float] = {}

        if self._collect_cpu:
            metrics["cpu_percent"] = psutil.cpu_percent(interval=1)

        if self._collect_memory:
            metrics["memory_percent"] = psutil.virtual_memory().percent

        if self._collect_disk:
            metrics["disk_percent"] = psutil.disk_usage(self._disk_path).percent

        return metrics

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
