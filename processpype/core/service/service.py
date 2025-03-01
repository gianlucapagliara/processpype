"""Base service class for ProcessPype."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Self

from ..configuration.models import ServiceConfiguration
from ..logfire import get_service_logger
from ..models import ServiceState, ServiceStatus
from .manager import ServiceManager
from .router import ServiceRouter


class ConfigurationError(Exception):
    """Exception raised when a service is not properly configured."""

    pass


class Service(ABC):
    """Base class for all services.

    A service is composed of three main components:
    1. Service class: Handles lifecycle (start/stop) and configuration
    2. Manager: Handles business logic and state management
    3. Router: Handles HTTP endpoints and API
    """

    configuration_class: type[ServiceConfiguration]

    def __init__(self, name: str | None = None):
        """Initialize the service.

        Args:
            name: Optional service name override
        """
        self._name = name or self.__class__.__name__.lower().replace("service", "")
        self._logger: logging.Logger | None = None
        self._config: ServiceConfiguration | None = None
        self._status = ServiceStatus(
            state=ServiceState.INITIALIZED, error=None, metadata={}, is_configured=False
        )

        # Create manager and router
        self._manager = self.create_manager()
        self._router = self.create_router()

    @property
    def name(self) -> str:
        """Get the service name."""
        return self._name

    @property
    def logger(self) -> logging.Logger:
        """Get the service logger.

        Returns:
            A logger instance configured for this service.
        """
        if self._logger is None:
            self._logger = get_service_logger(self.name)
        return self._logger

    @property
    def router(self) -> ServiceRouter | None:
        """Get the service router.

        Returns:
            The FastAPI router for this service.
        """
        return self._router

    @property
    def status(self) -> ServiceStatus:
        """Get the service status.

        Returns:
            Current service status.
        """
        return self._status

    @property
    def manager(self) -> ServiceManager:
        """Get the service manager.

        Returns:
            The manager instance for this service.
        """
        return self._manager

    @property
    def config(self) -> ServiceConfiguration | None:
        """Get the service configuration.

        Returns:
            The service configuration.
        """
        return self._config

    def configure(self, config: ServiceConfiguration | dict[str, Any]) -> None:
        """Configure the service.

        Args:
            config: Service configuration
        """
        self.logger.info(f"Configuring {self.name} service", extra={"config": config})
        if isinstance(config, dict):
            config = self.configuration_class.model_validate(config)

        self._config = config
        self.status.metadata = config.model_dump(mode="json")
        self.status.is_configured = True
        self.status.state = ServiceState.CONFIGURED

        # Validate configuration
        self._validate_configuration()

        if self.config is not None and self.config.autostart:
            self.logger.info(
                f"Autostarting {self.name} service",
                extra={"service_state": self.status.state},
            )
            asyncio.ensure_future(self.start())

    def _validate_configuration(self) -> None:
        """Validate the service configuration.

        This method can be overridden by subclasses to perform additional validation.
        By default, it just checks that configuration exists.

        Raises:
            ConfigurationError: If configuration is invalid
        """
        if self._config is None:
            self.status.is_configured = False
            raise ConfigurationError(f"Service {self.name} has no configuration")

    def set_error(self, error: str) -> None:
        """Set service error.

        Args:
            error: Error message
        """
        self.status.error = error
        self.status.state = ServiceState.ERROR
        self.logger.error(error)

    def requires_configuration(self) -> bool:
        """Check if the service requires configuration before starting.

        This method can be overridden by subclasses to specify whether
        configuration is required before starting.

        Returns:
            True if configuration is required, False otherwise
        """
        return True

    @abstractmethod
    def create_manager(self) -> ServiceManager:
        """Create the service manager.

        Returns:
            A manager instance for this service.
        """
        pass

    def create_router(self) -> ServiceRouter:
        """Create the service router with lifecycle management endpoints.

        Returns:
            A router instance for this service with default lifecycle endpoints.
        """
        return ServiceRouter(
            name=self.name,
            get_status=lambda: self.status,
            start_service=self.start,
            stop_service=self.stop,
            configure_service=self.configure,
            configure_and_start_service=self.configure_and_start,
        )

    async def start(self) -> None:
        """Start the service.

        This method handles the common service startup logic:
        1. Validates configuration if required
        2. Updates service state
        3. Delegates to the manager for service-specific startup

        Subclasses can override this method to add custom startup logic,
        but should call super().start() first.

        Raises:
            ConfigurationError: If service is not properly configured
            Exception: If service fails to start
        """
        if self.status.state not in [
            ServiceState.INITIALIZED,
            ServiceState.CONFIGURED,
            ServiceState.STOPPED,
        ]:
            raise RuntimeError(
                f"Service {self.name} cannot be started from state {self.status.state}"
            )

        self.logger.info(
            f"Starting {self.name} service", extra={"service_state": self.status.state}
        )

        # Validate configuration before starting if required
        if self.requires_configuration() and not self.status.is_configured:
            error_msg = f"Service {self.name} must be configured before starting"
            self.set_error(error_msg)
            raise ConfigurationError(error_msg)

        self.status.state = ServiceState.STARTING
        self.status.error = None

        try:
            # Delegate to the manager for service-specific startup
            await self.manager.start()
            self.status.state = ServiceState.RUNNING
        except Exception as e:
            error_msg = f"Failed to start {self.name} service: {e}"
            self.logger.error(
                error_msg, extra={"error": str(e), "service_state": self.status.state}
            )
            self.set_error(error_msg)
            raise

    async def stop(self) -> None:
        """Stop the service.

        This method handles the common service shutdown logic:
        1. Updates service state
        2. Delegates to the manager for service-specific shutdown

        Subclasses can override this method to add custom shutdown logic,
        but should call super().stop() first.
        """
        self.logger.info(
            f"Stopping {self.name} service", extra={"service_state": self.status.state}
        )
        self.status.state = ServiceState.STOPPING

        try:
            # Delegate to the manager for service-specific shutdown
            await self.manager.stop()
            self.status.state = ServiceState.STOPPED
        except Exception as e:
            error_msg = f"Failed to stop {self.name} service: {e}"
            self.logger.error(
                error_msg, extra={"error": str(e), "service_state": self.status.state}
            )
            self.set_error(error_msg)

    async def configure_and_start(
        self, config: ServiceConfiguration | dict[str, Any]
    ) -> Self:
        """Configure and start the service in one operation.

        This is a convenience method that combines configuration and startup.

        Args:
            config: Service configuration

        Returns:
            Self for method chaining

        Raises:
            ConfigurationError: If configuration is invalid
            Exception: If service fails to start
        """
        self.configure(config)
        await self.start()
        return self
