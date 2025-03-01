"""Cronitor service manager."""

import asyncio
import logging
from typing import Any

import cronitor

from processpype.core.service.manager import ServiceManager


class CronitorManager(ServiceManager):
    """Manager for Cronitor operations."""

    def __init__(self, logger: logging.Logger):
        """Initialize the Cronitor manager.

        Args:
            logger: Logger instance for Cronitor operations
        """
        super().__init__(logger)
        self._api_key: str = ""
        self._monitor_key: str = ""
        self._interval: float = 60.0
        self._state: str = "run"
        self._environment: str = ""
        self._series: str = ""
        self._metrics: dict[str, float] = {}
        self._ping_task: asyncio.Task[None] | None = None

    def set_api_key(self, api_key: str) -> None:
        """Set the Cronitor API key.

        Args:
            api_key: Cronitor API key
        """
        self._api_key = api_key
        cronitor.api_key = api_key
        self.logger.debug(
            "Updated Cronitor API key",
            extra={"api_key_set": bool(api_key)},
        )

    def set_monitor_key(self, monitor_key: str) -> None:
        """Set the Cronitor monitor key.

        Args:
            monitor_key: Cronitor monitor key
        """
        self._monitor_key = monitor_key
        self.logger.debug(
            "Updated Cronitor monitor key",
            extra={"monitor_key": monitor_key},
        )

    def set_interval(self, interval: float) -> None:
        """Set the ping interval.

        Args:
            interval: Interval in seconds between Cronitor pings
        """
        self._interval = interval
        self.logger.debug(
            "Updated ping interval",
            extra={"interval": interval},
        )

    def set_state(self, state: str) -> None:
        """Set the state to report to Cronitor.

        Args:
            state: State to report (run, complete, fail)
        """
        self._state = state
        self.logger.debug(
            "Updated ping state",
            extra={"state": state},
        )

    def set_environment(self, environment: str) -> None:
        """Set the environment to report to Cronitor.

        Args:
            environment: Environment to report
        """
        self._environment = environment
        self.logger.debug(
            "Updated environment",
            extra={"environment": environment},
        )

    def set_series(self, series: str) -> None:
        """Set the series identifier for the ping.

        Args:
            series: Series identifier
        """
        self._series = series
        self.logger.debug(
            "Updated series",
            extra={"series": series},
        )

    def set_metrics(self, metrics: dict[str, float]) -> None:
        """Set the metrics to include with the ping.

        Args:
            metrics: Metrics to include
        """
        self._metrics = metrics
        self.logger.debug(
            "Updated metrics",
            extra={"metrics": metrics},
        )

    async def start(self) -> None:
        """Start the Cronitor manager."""
        await self.start_pinging()

    async def stop(self) -> None:
        """Stop the Cronitor manager."""
        await self.stop_pinging()

    async def start_pinging(self) -> None:
        """Start the pinging loop."""
        if not self._api_key or not self._monitor_key:
            self.logger.warning(
                "Cannot start Cronitor pinging: missing API key or monitor key"
            )
            return

        self._ping_task = asyncio.create_task(self._ping_loop())
        self.logger.info("Started Cronitor pinging loop")

    async def stop_pinging(self) -> None:
        """Stop the pinging loop."""
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
            self._ping_task = None
            self.logger.info("Stopped Cronitor pinging loop")

    async def _ping_cronitor(self) -> None:
        """Send a ping to Cronitor."""
        try:
            # Prepare ping parameters
            params: dict[str, Any] = {"state": self._state}

            if self._environment:
                params["env"] = self._environment

            if self._series:
                params["series"] = self._series

            if self._metrics:
                for key, value in self._metrics.items():
                    params[f"metric[{key}]"] = value

            # Send ping using the Cronitor library
            monitor = cronitor.Monitor(self._monitor_key)
            await asyncio.to_thread(monitor.ping, **params)

            self.logger.debug(
                "Sent Cronitor ping",
                extra={
                    "monitor_key": self._monitor_key,
                    "state": self._state,
                    "params": params,
                },
            )
        except Exception as e:
            self.logger.error(
                "Error sending Cronitor ping",
                extra={"error": str(e)},
            )

    async def _ping_loop(self) -> None:
        """Ping loop for sending pings to Cronitor."""
        while True:
            try:
                await self._ping_cronitor()
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    "Error in Cronitor ping loop",
                    extra={"error": str(e)},
                )
                await asyncio.sleep(self._interval)
