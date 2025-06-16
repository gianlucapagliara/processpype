"""CloudWatch monitoring manager."""

import asyncio
import logging
import platform
import socket
import time
from datetime import datetime
from typing import Any

import boto3
import psutil
from botocore.exceptions import BotoCoreError, ClientError

from processpype.core.service.manager import ServiceManager


class CloudWatchManager(ServiceManager):
    """Manager for CloudWatch monitoring operations."""

    def __init__(self, logger: logging.Logger):
        """Initialize the CloudWatch monitoring manager.

        Args:
            logger: Logger instance for monitoring operations
        """
        super().__init__(logger)
        self._metrics: dict[str, float] = {}
        self._custom_metrics: dict[str, dict[str, Any]] = {}
        self._monitor_task: asyncio.Task[None] | None = None
        self._interval = 60.0  # seconds
        self._cloudwatch_client = None
        self._namespace = "ProcessPype"
        self._region = "us-east-1"
        self._dimensions: list[dict[str, str]] = []

        # Collection settings
        self._collect_cpu = True
        self._collect_memory = True
        self._collect_disk = True
        self._disk_path = "/"

        # Auto-detect instance information
        self._hostname = socket.gethostname()
        self._instance_id: str | None = None
        self._instance_name: str | None = None

    def configure_cloudwatch(
        self,
        region: str,
        namespace: str,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        instance_id: str | None = None,
        instance_name: str | None = None,
    ) -> None:
        """Configure the CloudWatch client.

        Args:
            region: AWS region for CloudWatch
            namespace: CloudWatch namespace for metrics
            access_key_id: AWS access key ID (optional)
            secret_access_key: AWS secret access key (optional)
            instance_id: Instance ID to use as a dimension (optional)
            instance_name: Instance name to use as a dimension (optional)
        """
        self._region = region
        self._namespace = namespace
        self._instance_id = instance_id
        self._instance_name = instance_name

        # Create CloudWatch client
        kwargs = {"region_name": region}
        if access_key_id and secret_access_key:
            kwargs["aws_access_key_id"] = access_key_id
            kwargs["aws_secret_access_key"] = secret_access_key

        self._cloudwatch_client = boto3.client("cloudwatch", **kwargs)

        # Setup dimensions
        self._dimensions = []
        if self._instance_id:
            self._dimensions.append({"Name": "InstanceId", "Value": self._instance_id})
        if self._instance_name:
            self._dimensions.append(
                {"Name": "InstanceName", "Value": self._instance_name}
            )

        # Always include hostname as a dimension
        self._dimensions.append({"Name": "HostName", "Value": self._hostname})

        # Include OS information
        self._dimensions.append({"Name": "Platform", "Value": platform.system()})

        self.logger.info(
            "CloudWatch client configured",
            extra={
                "region": region,
                "namespace": namespace,
                "dimensions": self._dimensions,
            },
        )

    def set_interval(self, interval: float) -> None:
        """Set the monitoring interval.

        Args:
            interval: Interval in seconds between metric collections
        """
        self._interval = interval
        self.logger.debug(
            "Updated CloudWatch monitoring interval",
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
            "Updated metric collection settings",
            extra={
                "collect_cpu": collect_cpu,
                "collect_memory": collect_memory,
                "collect_disk": collect_disk,
                "disk_path": disk_path,
            },
        )

    def add_custom_metric(
        self,
        name: str,
        value: float,
        unit: str = "None",
        dimensions: list[dict[str, str]] | None = None,
        namespace: str | None = None,
    ) -> None:
        """Add or update a custom metric.

        Args:
            name: The name of the metric
            value: The current value of the metric
            unit: CloudWatch unit (None, Count, Bytes, Seconds, Percent, etc.)
            dimensions: Additional dimensions for this metric (optional)
            namespace: Custom namespace for this metric (optional)
        """
        self._custom_metrics[name] = {
            "value": value,
            "unit": unit,
            "dimensions": dimensions or self._dimensions,
            "namespace": namespace or self._namespace,
            "timestamp": datetime.utcnow(),
        }

        self.logger.debug(
            f"Added/updated custom metric: {name}",
            extra={
                "metric_name": name,
                "value": value,
                "unit": unit,
                "namespace": namespace or self._namespace,
            },
        )

    def remove_custom_metric(self, name: str) -> bool:
        """Remove a custom metric.

        Args:
            name: The name of the metric to remove

        Returns:
            True if the metric was removed, False if it didn't exist
        """
        if name in self._custom_metrics:
            del self._custom_metrics[name]
            self.logger.debug(f"Removed custom metric: {name}")
            return True
        return False

    def get_custom_metrics(self) -> dict[str, dict[str, Any]]:
        """Get all custom metrics.

        Returns:
            Dictionary of custom metrics
        """
        return self._custom_metrics

    def get_custom_metric(self, name: str) -> dict[str, Any] | None:
        """Get a specific custom metric.

        Args:
            name: The name of the metric

        Returns:
            The metric data or None if not found
        """
        return self._custom_metrics.get(name)

    @property
    def metrics(self) -> dict[str, float]:
        """Get current system metrics."""
        # Combine system metrics with custom metrics values
        combined_metrics = self._metrics.copy()
        for name, metric_data in self._custom_metrics.items():
            combined_metrics[name] = metric_data["value"]
        return combined_metrics

    async def start(self) -> None:
        """Start the CloudWatch monitoring manager."""
        await super().start()
        await self.start_monitoring()

    async def stop(self) -> None:
        """Stop the CloudWatch monitoring manager."""
        await self.stop_monitoring()
        await super().stop()

    async def start_monitoring(self) -> None:
        """Start the monitoring loop."""
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            self.logger.info("Started CloudWatch monitoring")

    async def stop_monitoring(self) -> None:
        """Stop the monitoring loop."""
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
            self.logger.info("Stopped CloudWatch monitoring")

    async def _collect_metrics(self) -> dict[str, float]:
        """Collect system metrics.

        Returns:
            Dictionary of metric name to value
        """
        metrics = {}

        # Collect CPU metrics
        if self._collect_cpu:
            metrics["CPUUtilization"] = psutil.cpu_percent(interval=None)

        # Collect memory metrics
        if self._collect_memory:
            memory = psutil.virtual_memory()
            metrics["MemoryUtilization"] = memory.percent
            metrics["MemoryAvailable"] = memory.available / (1024 * 1024)  # MB
            metrics["MemoryUsed"] = memory.used / (1024 * 1024)  # MB

        # Collect disk metrics
        if self._collect_disk:
            disk = psutil.disk_usage(self._disk_path)
            metrics["DiskUtilization"] = disk.percent
            metrics["DiskAvailable"] = disk.free / (1024 * 1024 * 1024)  # GB
            metrics["DiskUsed"] = disk.used / (1024 * 1024 * 1024)  # GB

        return metrics

    async def _send_metrics_to_cloudwatch(self, metrics: dict[str, float]) -> None:
        """Send metrics to CloudWatch.

        Args:
            metrics: Dictionary of metric name to value
        """
        if not self._cloudwatch_client:
            self.logger.warning(
                "CloudWatch client not configured, skipping metric submission"
            )
            return

        try:
            timestamp = datetime.utcnow()
            system_metric_data = []

            # Process system metrics
            for name, value in metrics.items():
                system_metric_data.append(
                    {
                        "MetricName": name,
                        "Dimensions": self._dimensions,
                        "Timestamp": timestamp,
                        "Value": value,
                        "Unit": "Percent"
                        if name.endswith("Utilization")
                        else "Megabytes"
                        if name.endswith("Available") or name.endswith("Used")
                        else "None",
                    }
                )

            # Group custom metrics by namespace
            custom_metrics_by_namespace: dict[str, list[dict[str, Any]]] = {}
            for name, metric_data in self._custom_metrics.items():
                namespace = metric_data["namespace"]
                if namespace not in custom_metrics_by_namespace:
                    custom_metrics_by_namespace[namespace] = []

                custom_metrics_by_namespace[namespace].append(
                    {
                        "MetricName": name,
                        "Dimensions": metric_data["dimensions"],
                        "Timestamp": metric_data["timestamp"],
                        "Value": metric_data["value"],
                        "Unit": metric_data["unit"],
                    }
                )

            # Send system metrics
            if system_metric_data:
                # CloudWatch API has a limit of 20 metrics per request
                for i in range(0, len(system_metric_data), 20):
                    batch = system_metric_data[i : i + 20]
                    await asyncio.to_thread(
                        self._cloudwatch_client.put_metric_data,
                        Namespace=self._namespace,
                        MetricData=batch,
                    )

                self.logger.debug(
                    "Sent system metrics to CloudWatch",
                    extra={
                        "metric_count": len(system_metric_data),
                        "namespace": self._namespace,
                    },
                )

            # Send custom metrics grouped by namespace
            for namespace, metrics_data in custom_metrics_by_namespace.items():
                # CloudWatch API has a limit of 20 metrics per request
                for i in range(0, len(metrics_data), 20):
                    batch = metrics_data[i : i + 20]
                    await asyncio.to_thread(
                        self._cloudwatch_client.put_metric_data,
                        Namespace=namespace,
                        MetricData=batch,
                    )

                self.logger.debug(
                    "Sent custom metrics to CloudWatch",
                    extra={"metric_count": len(metrics_data), "namespace": namespace},
                )

        except (BotoCoreError, ClientError) as e:
            self.logger.error(
                f"Error sending metrics to CloudWatch: {e}",
                extra={"error": str(e)},
            )
        except Exception as e:
            self.logger.error(
                f"Unexpected error sending metrics to CloudWatch: {e}",
                extra={"error": str(e)},
            )

    async def _monitor_loop(self) -> None:
        """Monitor system metrics and send to CloudWatch periodically."""
        self.logger.info("Starting CloudWatch monitoring loop")
        while True:
            start_time = time.time()
            try:
                # Collect metrics
                self._metrics = await self._collect_metrics()

                # Send metrics to CloudWatch
                await self._send_metrics_to_cloudwatch(self._metrics)

            except Exception as e:
                self.logger.error(
                    f"Error in CloudWatch monitoring loop: {e}",
                    extra={"error": str(e)},
                )

            # Sleep for the remaining interval time
            elapsed = time.time() - start_time
            sleep_time = max(0.1, self._interval - elapsed)
            await asyncio.sleep(sleep_time)
