"""Base service class for ProcessPype."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Self

from processpype.config.models import ServiceConfiguration

from .manager import ServiceManager
from .models import ServiceState, ServiceStatus


class ConfigurationError(Exception):
    """Raised when a service is not properly configured."""


class Service(ABC):
    """Base class for all services.

    A service is composed of three main components:
    1. Service class: Handles lifecycle (start/stop) and configuration
    2. Manager: Handles business logic and state management
    3. Router: Handles HTTP endpoints and API
    """

    configuration_class: type[ServiceConfiguration]

    def __init__(self, name: str | None = None) -> None:
        self._name = name or self.__class__.__name__.lower().replace("service", "")
        self._logger: logging.Logger | None = None
        self._config: ServiceConfiguration | None = None
        self._status = ServiceStatus(
            state=ServiceState.INITIALIZED, error=None, metadata={}, is_configured=False
        )
        self._manager = self.create_manager()
        self._router: Any = self.create_router()

    @property
    def name(self) -> str:
        return self._name

    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            self._logger = logging.getLogger(f"processpype.services.{self.name}")
        return self._logger

    @property
    def router(self) -> Any:
        return self._router

    @property
    def status(self) -> ServiceStatus:
        return self._status

    @property
    def manager(self) -> ServiceManager:
        return self._manager

    @property
    def config(self) -> ServiceConfiguration | None:
        return self._config

    def configure(self, config: ServiceConfiguration | dict[str, Any]) -> None:
        self.logger.info(f"Configuring {self.name} service", extra={"config": config})
        if isinstance(config, dict):
            config = self.configuration_class.model_validate(config)

        self._config = config
        self.status.metadata = config.model_dump(mode="json")
        self.status.is_configured = True
        self.status.state = ServiceState.CONFIGURED

        self._validate_configuration()

        if self.config is not None and self.config.autostart:
            self.logger.info(
                f"Autostarting {self.name} service",
                extra={"service_state": self.status.state},
            )
            asyncio.ensure_future(self.start())

    def _validate_configuration(self) -> None:
        if self._config is None:
            self.status.is_configured = False
            raise ConfigurationError(f"Service {self.name} has no configuration")

    def set_error(self, error: str) -> None:
        self.status.error = error
        self.status.state = ServiceState.ERROR
        self.logger.error(error)

    def requires_configuration(self) -> bool:
        return True

    @abstractmethod
    def create_manager(self) -> ServiceManager:
        """Create the service manager."""

    def create_router(self) -> Any:
        """Create the service router with lifecycle management endpoints.

        Import is deferred to avoid requiring FastAPI at import time
        when only the service base is needed.
        """
        from processpype.server.service_router import ServiceRouter

        return ServiceRouter(
            name=self.name,
            get_status=lambda: self.status,
            start_service=self.start,
            stop_service=self.stop,
            configure_service=self.configure,
            configure_and_start_service=self.configure_and_start,
        )

    async def start(self) -> None:
        if self.status.state not in [
            ServiceState.INITIALIZED,
            ServiceState.CONFIGURED,
            ServiceState.STOPPED,
        ]:
            raise RuntimeError(
                f"Service {self.name} cannot be started from state {self.status.state}"
            )

        self.logger.info(
            f"Starting {self.name} service",
            extra={"service_state": self.status.state},
        )

        if self.requires_configuration() and not self.status.is_configured:
            error_msg = f"Service {self.name} must be configured before starting"
            self.set_error(error_msg)
            raise ConfigurationError(error_msg)

        self.status.state = ServiceState.STARTING
        self.status.error = None

        try:
            await self.manager.start()
            self.status.state = ServiceState.RUNNING
        except Exception as e:
            error_msg = f"Failed to start {self.name} service: {e}"
            self.logger.error(
                error_msg,
                extra={"error": str(e), "service_state": self.status.state},
            )
            self.set_error(error_msg)
            raise

    async def stop(self) -> None:
        self.logger.info(
            f"Stopping {self.name} service",
            extra={"service_state": self.status.state},
        )
        self.status.state = ServiceState.STOPPING

        try:
            await self.manager.stop()
            self.status.state = ServiceState.STOPPED
        except Exception as e:
            error_msg = f"Failed to stop {self.name} service: {e}"
            self.logger.error(
                error_msg,
                extra={"error": str(e), "service_state": self.status.state},
            )
            self.set_error(error_msg)

    async def configure_and_start(
        self, config: ServiceConfiguration | dict[str, Any]
    ) -> Self:
        self.configure(config)
        await self.start()
        return self
