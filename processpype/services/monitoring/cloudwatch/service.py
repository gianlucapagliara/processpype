"""CloudWatch monitoring service."""

from typing import TYPE_CHECKING

from processpype.core.service.router import ServiceRouter
from processpype.core.service.service import Service
from processpype.services import register_service_class

from .config import CloudWatchConfiguration
from .manager import CloudWatchManager
from .router import CloudWatchRouter


@register_service_class
class CloudWatchService(Service):
    """Service for sending metrics to AWS CloudWatch."""

    configuration_class = CloudWatchConfiguration

    if TYPE_CHECKING:
        manager: CloudWatchManager
        config: CloudWatchConfiguration

    def __init__(self, name: str | None = None):
        """Initialize the CloudWatch monitoring service.

        Args:
            name: Optional service name override
        """
        name = name or "cloudwatch"
        super().__init__(name)

    def create_manager(self) -> CloudWatchManager:
        """Create the CloudWatch manager.

        Returns:
            A CloudWatch manager instance.
        """
        return CloudWatchManager(
            logger=self.logger,
        )

    def create_router(self) -> ServiceRouter:
        """Create the CloudWatch service router.

        Returns:
            A CloudWatch service router instance.
        """
        return CloudWatchRouter(
            name=self.name,
            get_status=lambda: self.status,
            get_metrics=lambda: self.manager.metrics,
            start_service=self.start,
            stop_service=self.stop,
            configure_service=self.configure,
            configure_and_start_service=self.configure_and_start,
            # Pass custom metric management methods
            add_custom_metric=self.manager.add_custom_metric,
            get_custom_metrics=self.manager.get_custom_metrics,
            get_custom_metric=self.manager.get_custom_metric,
            remove_custom_metric=self.manager.remove_custom_metric,
        )

    async def start(self) -> None:
        """Start the CloudWatch monitoring service.

        This method configures the manager with the service configuration
        and AWS credentials before starting it.
        """
        await super().start()

        # If we have a configuration, update the manager's settings
        if self.config:
            # Configure CloudWatch client
            self.manager.configure_cloudwatch(
                region=self.config.region,
                namespace=self.config.namespace,
                access_key_id=self.config.access_key_id,
                secret_access_key=self.config.secret_access_key,
                instance_id=self.config.instance_id,
                instance_name=self.config.instance_name,
            )

            # Configure monitoring settings
            self.manager.set_interval(self.config.interval)
            self.manager.set_collection_settings(
                collect_cpu=self.config.collect_cpu,
                collect_memory=self.config.collect_memory,
                collect_disk=self.config.collect_disk,
                disk_path=self.config.disk_path,
            )
