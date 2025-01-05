"""Base manager classes for ProcessPype."""

import logging


class ServiceManager:
    """Base class for all service managers.

    A service manager handles the business logic and state management for a service.
    It is responsible for the core functionality of the service, while the service
    class itself handles lifecycle and the router handles HTTP endpoints.
    """

    def __init__(self, logger: logging.Logger):
        """Initialize the service manager.

        Args:
            logger: Logger instance for manager operations
        """
        self._logger = logger

    @property
    def logger(self) -> logging.Logger:
        """Get the manager logger."""
        return self._logger
