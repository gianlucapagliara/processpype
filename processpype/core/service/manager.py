"""Base service manager class for ProcessPype."""

import logging
from abc import ABC


class ServiceManager(ABC):
    """Base class for service managers.

    A service manager is responsible for handling the business logic
    and state management for a service.
    """

    def __init__(self, logger: logging.Logger):
        """Initialize the service manager.

        Args:
            logger: Logger instance for service operations
        """
        self._logger = logger

    @property
    def logger(self) -> logging.Logger:
        """Get the service logger.

        Returns:
            A logger instance configured for this service.
        """
        return self._logger

    async def start(self) -> None:
        """Start the service manager.

        This method should be implemented by subclasses to handle
        service-specific startup logic. The default implementation
        does nothing.

        Raises:
            Exception: If the service fails to start
        """
        pass

    async def stop(self) -> None:
        """Stop the service manager.

        This method should be implemented by subclasses to handle
        service-specific shutdown logic. The default implementation
        does nothing.
        """
        pass
