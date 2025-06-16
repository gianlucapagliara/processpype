"""Configuration models for the CloudWatch monitoring service."""

from pydantic import Field, field_validator

from processpype.core.configuration.models import ServiceConfiguration


class CloudWatchConfiguration(ServiceConfiguration):
    """Configuration for the CloudWatch monitoring service."""

    region: str = Field(
        default="us-east-1",
        description="AWS region for CloudWatch",
    )

    namespace: str = Field(
        default="ProcessPype",
        description="CloudWatch namespace for metrics",
    )

    interval: float = Field(
        default=60.0,
        description="Interval in seconds between metric submissions to CloudWatch",
        ge=1.0,
    )

    # AWS credentials are optional because they can be provided via environment variables
    # or IAM roles when running on AWS infrastructure
    access_key_id: str | None = Field(
        default=None,
        description="AWS access key ID (optional if using IAM roles or environment variables)",
    )

    secret_access_key: str | None = Field(
        default=None,
        description="AWS secret access key (optional if using IAM roles or environment variables)",
    )

    # Metrics to collect and send
    collect_cpu: bool = Field(
        default=True,
        description="Whether to collect CPU metrics",
    )

    collect_memory: bool = Field(
        default=True,
        description="Whether to collect memory metrics",
    )

    collect_disk: bool = Field(
        default=True,
        description="Whether to collect disk metrics",
    )

    disk_path: str = Field(
        default="/",
        description="Path to monitor for disk usage",
    )

    # Dimension configuration
    instance_id: str | None = Field(
        default=None,
        description="Instance ID to use as a dimension (default: auto-detected)",
    )

    instance_name: str | None = Field(
        default=None,
        description="Instance name to use as a dimension",
    )

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, value: float) -> float:
        """Validate the interval value.

        Args:
            value: The interval value to validate

        Returns:
            The validated interval value

        Raises:
            ValueError: If the interval is less than 1.0
        """
        if value < 1.0:
            raise ValueError("Input should be greater than or equal to 1")
        return value
