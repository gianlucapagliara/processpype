"""Base service manager class for ProcessPype."""

import logging
from abc import ABC, abstractmethod


class ServiceManager(ABC):
    """Base class for service managers.

    A service manager handles the business logic and state management for a service.
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @abstractmethod
    async def start(self) -> None:
        """Start the service manager."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the service manager."""
