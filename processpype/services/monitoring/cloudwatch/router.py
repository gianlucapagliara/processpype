"""Router for CloudWatch monitoring service."""

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

from processpype.core.models import ServiceStatus
from processpype.core.service.router import ServiceRouter

from .config import CloudWatchConfiguration


class CustomMetricModel(BaseModel):
    """Model for a custom metric."""

    name: str = Field(..., description="The name of the metric")
    value: float = Field(..., description="The current value of the metric")
    unit: str = Field(
        default="None",
        description="CloudWatch unit (None, Count, Bytes, Seconds, Percent, etc.)",
    )
    dimensions: list[dict[str, str]] | None = Field(
        default=None, description="Additional dimensions for this metric (optional)"
    )
    namespace: str | None = Field(
        default=None, description="Custom namespace for this metric (optional)"
    )


class CloudWatchRouter(ServiceRouter):
    """Router for CloudWatch monitoring service."""

    def __init__(
        self,
        name: str,
        get_status: Callable[[], ServiceStatus],
        get_metrics: Callable[[], dict[str, float]],
        start_service: Callable[[], Any],
        stop_service: Callable[[], Any],
        configure_service: Callable[[Any], Any],
        configure_and_start_service: Callable[[Any], Any],
        # Add parameters for custom metrics management
        add_custom_metric: Callable[
            [str, float, str, list[dict[str, str]] | None, str | None], None
        ]
        | None = None,
        get_custom_metrics: Callable[[], dict[str, dict[str, Any]]] | None = None,
        get_custom_metric: Callable[[str], dict[str, Any] | None] | None = None,
        remove_custom_metric: Callable[[str], bool] | None = None,
    ):
        """Initialize the CloudWatch router.

        This router extends the base service router with additional
        endpoints specific to CloudWatch monitoring.

        Args:
            name: Service name
            get_status: Function to get service status
            get_metrics: Function to get current metrics
            start_service: Function to start the service
            stop_service: Function to stop the service
            configure_service: Function to configure the service
            configure_and_start_service: Function to configure and start the service
            add_custom_metric: Function to add a custom metric
            get_custom_metrics: Function to get all custom metrics
            get_custom_metric: Function to get a specific custom metric
            remove_custom_metric: Function to remove a custom metric
        """
        super().__init__(
            name=name,
            get_status=get_status,
            start_service=start_service,
            stop_service=stop_service,
            configure_service=configure_service,
            configure_and_start_service=configure_and_start_service,
        )

        self._add_custom_metric = add_custom_metric
        self._get_custom_metrics = get_custom_metrics
        self._get_custom_metric = get_custom_metric
        self._remove_custom_metric = remove_custom_metric

        # Register additional endpoints - the 'self' is an APIRouter
        @self.get("/metrics", tags=["monitoring", "cloudwatch"])
        async def get_current_metrics() -> dict[str, float]:
            """Get the current metrics from CloudWatch monitoring.

            Returns:
                Dictionary of metrics
            """
            metrics = get_metrics()
            if not metrics:
                raise HTTPException(
                    status_code=404,
                    detail="No metrics available. Ensure the service is running.",
                )
            return metrics

        # Override the configure endpoint to use our custom configuration class
        @self.post("/configure", tags=["monitoring", "cloudwatch"])
        async def update_configuration(
            config: CloudWatchConfiguration,
        ) -> ServiceStatus:
            """Update the CloudWatch monitoring configuration.

            Args:
                config: New configuration

            Returns:
                Updated service status
            """
            configure_service(config)
            return get_status()

        # Add custom metrics endpoints if the functions are provided
        if (
            self._add_custom_metric
            and self._get_custom_metrics
            and self._get_custom_metric
            and self._remove_custom_metric
        ):
            # Store the functions in local variables to ensure type checking knows they aren't None
            _add_metric_fn = self._add_custom_metric
            _get_metrics_fn = self._get_custom_metrics
            _get_metric_fn = self._get_custom_metric
            _remove_metric_fn = self._remove_custom_metric

            @self.post("/metrics/custom", tags=["monitoring", "cloudwatch"])
            async def add_metric(metric: CustomMetricModel) -> dict[str, str]:
                """Add or update a custom metric.

                Args:
                    metric: The custom metric to add or update

                Returns:
                    Status message
                """
                _add_metric_fn(
                    metric.name,
                    metric.value,
                    metric.unit,
                    metric.dimensions,
                    metric.namespace,
                )
                return {
                    "status": "success",
                    "message": f"Custom metric '{metric.name}' added/updated",
                }

            @self.get("/metrics/custom", tags=["monitoring", "cloudwatch"])
            async def list_custom_metrics() -> dict[str, dict[str, Any]]:
                """Get all custom metrics.

                Returns:
                    Dictionary of custom metrics
                """
                metrics = _get_metrics_fn()
                return metrics

            @self.get("/metrics/custom/{name}", tags=["monitoring", "cloudwatch"])
            async def get_metric(name: str) -> dict[str, Any]:
                """Get a specific custom metric.

                Args:
                    name: The name of the metric

                Returns:
                    The metric data
                """
                metric = _get_metric_fn(name)
                if not metric:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Custom metric '{name}' not found",
                    )
                return metric

            @self.delete("/metrics/custom/{name}", tags=["monitoring", "cloudwatch"])
            async def delete_metric(name: str) -> dict[str, str]:
                """Remove a custom metric.

                Args:
                    name: The name of the metric to remove

                Returns:
                    Status message
                """
                if not _remove_metric_fn(name):
                    raise HTTPException(
                        status_code=404,
                        detail=f"Custom metric '{name}' not found",
                    )
                return {
                    "status": "success",
                    "message": f"Custom metric '{name}' removed",
                }
