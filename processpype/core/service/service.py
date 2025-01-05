"""Base service class for ProcessPype."""

import logging
from abc import ABC, abstractmethod

from ..configuration.models import ServiceConfiguration
from ..logfire import get_service_logger
from ..models import ServiceState, ServiceStatus
from .manager import ServiceManager
from .router import ServiceRouter


class Service(ABC):
    """Base class for all services.

    A service is composed of three main components:
    1. Service class: Handles lifecycle (start/stop) and configuration
    2. Manager: Handles business logic and state management
    3. Router: Handles HTTP endpoints and API
    """

    def __init__(self, name: str | None = None):
        """Initialize the service.

        Args:
            name: Optional service name override
        """
        self._name = name or self.__class__.__name__.lower().replace("service", "")
        self._logger: logging.Logger | None = None
        self._config: ServiceConfiguration | None = None
        self._status = ServiceStatus(
            state=ServiceState.INITIALIZED, error=None, metadata={}
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

    def configure(self, config: ServiceConfiguration) -> None:
        """Configure the service.

        Args:
            config: Service configuration
        """
        self._config = config
        self.status.metadata.update(config.metadata)

    def set_error(self, error: str) -> None:
        """Set service error.

        Args:
            error: Error message
        """
        self.status.error = error
        self.logger.error(error)

    @abstractmethod
    def create_manager(self) -> ServiceManager:
        """Create the service manager.

        Returns:
            A manager instance for this service.
        """
        pass

    @abstractmethod
    def create_router(self) -> ServiceRouter:
        """Create the service router.

        Returns:
            A router instance for this service.
        """
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start the service."""
        self.logger.info("Starting service")
        self.status.state = ServiceState.STARTING
        self.status.error = None

    @abstractmethod
    async def stop(self) -> None:
        """Stop the service."""
        self.logger.info("Stopping service")
        self.status.state = ServiceState.STOPPING
