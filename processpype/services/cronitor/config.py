"""Configuration models for the Cronitor service."""

from pydantic import Field, field_validator

from processpype.core.configuration.models import ServiceConfiguration


class CronitorConfiguration(ServiceConfiguration):
    """Configuration for the Cronitor service."""

    api_key: str = Field(
        default="",
        description="Cronitor API key",
    )

    monitor_key: str = Field(
        default="",
        description="Cronitor monitor key to ping",
    )

    interval: float = Field(
        default=60.0,
        description="Interval in seconds between Cronitor pings",
        ge=1.0,
    )

    state: str = Field(
        default="run",
        description="State to report to Cronitor (run, complete, fail)",
    )

    environment: str = Field(
        default="",
        description="Environment to report to Cronitor",
    )

    series: str = Field(
        default="",
        description="Series identifier for the ping",
    )

    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Metrics to include with the ping",
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

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: str) -> str:
        """Validate the state value.

        Args:
            value: The state value to validate

        Returns:
            The validated state value

        Raises:
            ValueError: If the state is not one of the allowed values
        """
        allowed_states = ["run", "complete", "fail"]
        if value not in allowed_states:
            raise ValueError(f"State must be one of: {', '.join(allowed_states)}")
        return value
