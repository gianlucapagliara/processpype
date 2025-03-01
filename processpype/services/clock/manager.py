"""Clock service manager."""

import asyncio
from datetime import datetime
from logging import Logger
from typing import Any

from chronopype.clocks import get_clock_class
from chronopype.clocks.base import BaseClock
from chronopype.clocks.config import ClockConfig
from chronopype.clocks.modes import ClockMode

from processpype.core.service.manager import ServiceManager

from .config import ClockConfiguration


class ClockManager(ServiceManager):
    """Manager for the Clock service."""

    def __init__(self, logger: Logger) -> None:
        """Initialize the clock manager."""
        super().__init__(logger)
        self._clock: BaseClock | None = None
        self._config: ClockConfig | None = None
        self._clock_task: asyncio.Task | None = None

    def get_default_configuration(self) -> ClockConfiguration:
        """Get the default configuration for the clock manager."""
        return ClockConfiguration(
            mode=ClockMode.REALTIME,
            tick_size=1.0,
            start_time=0.0,
            end_time=0.0,
            processor_timeout=1.0,
            max_retries=0,
            concurrent_processors=False,
            stats_window_size=100,
        )

    def set_configuration(self, config: ClockConfiguration) -> None:
        """Configure the clock manager.

        Args:
            config: Clock configuration
        """
        # Create chronopype clock configuration
        self._config = config.get_clock_config()

        # Get appropriate clock class and create instance
        clock_class = get_clock_class(config.mode)
        self._clock = clock_class(self._config)

        self.logger.info(
            f"Clock configured with mode={config.mode}, tick_size={config.tick_size}s"
        )

    async def start(self) -> None:
        """Start the clock."""
        if self._clock is None:
            self.set_configuration(self.get_default_configuration())
        self._clock_task = asyncio.ensure_future(self.run_clock())

    async def stop(self) -> None:
        """Stop the clock."""
        if self._clock is None:
            return

        await self._clock.shutdown()

    def get_clock_status(self) -> dict[str, Any]:
        """Get the current status of the clock.

        Returns:
            Dictionary with clock status information
        """
        if self._clock is None or self._config is None:
            return {
                "configured": False,
                "running": False,
            }

        return {
            "configured": True,
            "mode": self._config.clock_mode,
            "tick_size": self._config.tick_size,
            "current_time": self._clock.current_timestamp,
            "current_time_iso": datetime.fromtimestamp(
                self._clock.current_timestamp
            ).isoformat(),
            "tick_counter": self._clock.tick_counter,
            "running": self._clock.processors
            != [],  # Clock is running if it has processors
        }

    async def run_clock(self) -> None:
        if self._clock is None:
            raise ValueError("Clock not initialized")

        async with self._clock as clock:
            await clock.run()
