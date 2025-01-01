"""Base service class for ProcessPype."""

import logging
from abc import ABC, abstractmethod

from fastapi import APIRouter

from .config.models import ServiceConfiguration
from .logfire import get_service_logger
from .models import ServiceState, ServiceStatus


class Service(ABC):
    """Base class for all services."""

    def __init__(self, name: str | None = None):
        """Initialize the service.

        Args:
            name: Optional service name override
        """
        self._name = name or self.__class__.__name__.lower().replace("service", "")
        self._logger: logging.Logger | None = None
        self._config: ServiceConfiguration | None = None

        # Create router with service prefix
        self._router = APIRouter(prefix=f"/services/{self.name}")
        self.setup_routes()

        self._status = ServiceStatus(
            state=ServiceState.INITIALIZED, error=None, metadata={}
        )

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
    def router(self) -> APIRouter:
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

    def setup_routes(self) -> None:
        """Setup service-specific routes."""

        @self._router.get("")
        async def get_status() -> ServiceStatus:
            """Get service status."""
            return self.status

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
