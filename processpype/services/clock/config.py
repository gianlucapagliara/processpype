"""Clock service configuration."""

from chronopype.clocks.config import ClockConfig
from chronopype.clocks.modes import ClockMode
from pydantic import Field, field_validator

from processpype.core.configuration.models import ServiceConfiguration


class ClockConfiguration(ServiceConfiguration):
    """Clock service configuration."""

    mode: ClockMode = Field(
        default=ClockMode.REALTIME,
        description="Clock mode (realtime or backtest)",
    )
    tick_size: float = Field(
        default=1.0,
        description="Size of each tick in seconds",
        gt=0,  # Must be greater than 0
    )
    start_time: float | None = Field(
        default=None,
        description="Start time for backtest mode (Unix timestamp)",
    )
    end_time: float | None = Field(
        default=None,
        description="End time for backtest mode (Unix timestamp)",
    )
    processor_timeout: float = Field(
        default=1.0,
        description="Timeout for processor execution in seconds",
    )
    max_retries: int = Field(
        default=0,
        description="Maximum number of retries for processor execution",
    )
    concurrent_processors: bool = Field(
        default=False,
        description="Allow concurrent processor execution",
    )
    stats_window_size: int = Field(
        default=100,
        description="Size of the stats window",
    )

    @field_validator("tick_size")
    def validate_tick_size(cls, v: float) -> float:
        """Validate tick size is positive."""
        if v <= 0:
            raise ValueError("tick_size must be positive")
        return v

    def get_clock_config(self) -> ClockConfig:
        """Get the clock configuration."""
        return ClockConfig(
            clock_mode=self.mode,
            tick_size=self.tick_size,
            start_time=self.start_time or 0.0,
            end_time=self.end_time or 0.0,
            processor_timeout=self.processor_timeout,
            max_retries=self.max_retries,
            stats_window_size=self.stats_window_size,
            concurrent_processors=self.concurrent_processors,
        )
