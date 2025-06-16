"""Configuration models for the monitoring service."""

from pydantic import Field, field_validator

from processpype.core.configuration.models import ServiceConfiguration


class SystemMonitoringConfiguration(ServiceConfiguration):
    """Configuration for the monitoring service."""

    interval: float = Field(
        default=5.0,
        description="Interval in seconds between metric collections",
        ge=1.0,
    )

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
