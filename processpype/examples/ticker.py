"""TickerService — Service with a background async loop."""

import asyncio
import logging
from typing import Any

from pydantic import Field

from processpype.config.models import ServiceConfiguration
from processpype.service import Service, ServiceManager


class TickerConfiguration(ServiceConfiguration):
    interval_seconds: float = Field(
        default=1.0, gt=0, description="Seconds between ticks"
    )


class TickerManager(ServiceManager):
    def __init__(self, logger: logging.Logger) -> None:
        super().__init__(logger)
        self._interval: float = 1.0
        self._tick_count: int = 0
        self._task: asyncio.Task[None] | None = None

    @property
    def tick_count(self) -> int:
        return self._tick_count

    def configure(self, config: TickerConfiguration) -> None:
        self._interval = config.interval_seconds

    async def start(self) -> None:
        self._tick_count = 0
        self._task = asyncio.create_task(self._tick_loop())
        self.logger.info(f"Ticker started (interval={self._interval}s)")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self.logger.info(f"Ticker stopped after {self._tick_count} ticks")

    async def _tick_loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            self._tick_count += 1
            self.logger.info(f"Tick #{self._tick_count}")


class TickerService(Service):
    """A service with a background async loop."""

    configuration_class = TickerConfiguration

    def create_manager(self) -> TickerManager:
        return TickerManager(self.logger)

    def configure(self, config: ServiceConfiguration | dict[str, Any]) -> None:
        super().configure(config)
        if isinstance(self.manager, TickerManager) and isinstance(
            self.config, TickerConfiguration
        ):
            self.manager.configure(self.config)

    def requires_configuration(self) -> bool:
        return False
