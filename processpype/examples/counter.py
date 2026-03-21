"""CounterService — Service with configuration and custom routes.

Demonstrates:
- Custom ServiceConfiguration with validation
- Custom ServiceRouter with domain-specific endpoints
- Stateful ServiceManager
"""

import logging
from collections.abc import Callable
from typing import Any

from pydantic import Field, field_validator

from processpype.core.configuration.models import ServiceConfiguration
from processpype.core.service import Service, ServiceManager
from processpype.core.service.router import ServiceRouter


class CounterConfiguration(ServiceConfiguration):
    """Configuration for the counter service."""

    initial_value: int = Field(default=0, description="Starting counter value")
    step: int = Field(default=1, description="Increment step size")

    @field_validator("step")
    @classmethod
    def step_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("step must be positive")
        return v


class CounterManager(ServiceManager):
    """Manager that maintains a simple counter."""

    def __init__(self, logger: logging.Logger) -> None:
        super().__init__(logger)
        self._value: int = 0
        self._step: int = 1

    @property
    def value(self) -> int:
        return self._value

    def configure(self, config: CounterConfiguration) -> None:
        self._value = config.initial_value
        self._step = config.step

    def increment(self) -> int:
        self._value += self._step
        self.logger.info(f"Counter incremented to {self._value}")
        return self._value

    def reset(self) -> int:
        self._value = 0
        self.logger.info("Counter reset to 0")
        return self._value

    async def start(self) -> None:
        self.logger.info(f"Counter started at {self._value} (step={self._step})")

    async def stop(self) -> None:
        self.logger.info(f"Counter stopped at {self._value}")


class CounterRouter(ServiceRouter):
    """Router with custom endpoints for counter operations."""

    def __init__(
        self,
        name: str,
        get_manager: "Callable[[], CounterManager]",
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, **kwargs)
        self._get_manager = get_manager
        self._setup_counter_routes()

    def _setup_counter_routes(self) -> None:
        @self.get("/value")
        async def get_value() -> dict[str, int]:
            """Get the current counter value."""
            return {"value": self._get_manager().value}

        @self.post("/increment")
        async def increment() -> dict[str, int]:
            """Increment the counter."""
            return {"value": self._get_manager().increment()}

        @self.post("/reset")
        async def reset() -> dict[str, int]:
            """Reset the counter to zero."""
            return {"value": self._get_manager().reset()}


class CounterService(Service):
    """A service with configuration and custom HTTP endpoints.

    Usage::

        app.register_service(CounterService)
        await app.start_service("counter")
        # POST /services/counter/increment
        # GET  /services/counter/value
        # POST /services/counter/reset
    """

    configuration_class = CounterConfiguration

    @property
    def _counter_manager(self) -> CounterManager:
        assert isinstance(self._manager, CounterManager)
        return self._manager

    def create_manager(self) -> CounterManager:
        return CounterManager(self.logger)

    def configure(self, config: ServiceConfiguration | dict[str, Any]) -> None:
        super().configure(config)
        if isinstance(self.config, CounterConfiguration):
            self._counter_manager.configure(self.config)

    def create_router(self) -> CounterRouter:
        return CounterRouter(
            name=self.name,
            get_manager=lambda: self._counter_manager,
            get_status=lambda: self.status,
            start_service=self.start,
            stop_service=self.stop,
            configure_service=self.configure,
            configure_and_start_service=self.configure_and_start,
        )

    def requires_configuration(self) -> bool:
        return False
