"""Service and lifecycle management for ProcessPype.

This module provides the core application manager responsible for:
- Service registration and configuration
- Service lifecycle management (start/stop)
- Application state tracking
- Error handling and logging
"""

import logging

from processpype.core.configuration.models import (
    ApplicationConfiguration,
    ServiceConfiguration,
)
from processpype.core.models import ServiceState
from processpype.core.service import Service


class ApplicationManager:
    """Manager for application services and lifecycle.

    Handles service registration, configuration, and lifecycle management.
    Maintains the overall application state and coordinates service operations.

    Attributes:
        state: Current application state
        services: Dictionary of registered services
    """

    def __init__(self, logger: logging.Logger, config: ApplicationConfiguration):
        """Initialize the application manager.

        Args:
            logger: Logger instance for application operations
            config: Application configuration containing service settings
        """
        self._logger = logger
        self._config = config
        self._services: dict[str, Service] = {}
        self._state = ServiceState.STOPPED

    @property
    def state(self) -> ServiceState:
        """Get the current application state.

        Returns:
            Current ServiceState of the application
        """
        return self._state

    @property
    def services(self) -> dict[str, Service]:
        """Get all registered services.

        Returns:
            Dictionary mapping service names to their instances
        """
        return self._services

    def register_service(
        self, service_class: type[Service], name: str | None = None
    ) -> Service:
        """Register a new service.

        Creates and configures a new service instance. If service configuration
        exists in the application config, it will be applied to the service.

        Args:
            service_class: Service class to instantiate
            name: Optional service name override

        Returns:
            The registered service instance

        Raises:
            ValueError: If service name is already registered
        """
        service = service_class(name)

        if service.name in self._services:
            raise ValueError(f"Service {service.name} already registered")

        # Apply service configuration if available
        if service.name in self._config.services:
            service_config = self._config.services[service.name]
            if hasattr(service, "configure"):
                if not isinstance(service_config, ServiceConfiguration):
                    service_config = ServiceConfiguration(**service_config)
                service.configure(service_config)

        self._services[service.name] = service
        self._logger.info(f"Registered service: {service.name}")
        return service

    def get_service(self, name: str) -> Service | None:
        """Get a service by name.

        Args:
            name: Service name to lookup

        Returns:
            Service instance if found, None otherwise
        """
        return self._services.get(name)

    async def start_service(self, service_name: str) -> None:
        """Start a service by name.

        Initiates the startup sequence for the specified service.

        Args:
            service_name: Name of the service to start

        Raises:
            ValueError: If service not found
        """
        service = self._services.get(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")
        await service.start()

    async def stop_service(self, service_name: str) -> None:
        """Stop a service by name.

        Initiates the shutdown sequence for the specified service.

        Args:
            service_name: Name of the service to stop

        Raises:
            ValueError: If service not found
        """
        service = self._services.get(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")
        await service.stop()

    async def start_enabled_services(self) -> None:
        """Start all enabled services.

        Attempts to start all services that are marked as enabled in the
        application configuration. Logs errors for failed starts but continues
        with remaining services.
        """
        for name, service in self._services.items():
            if name in self._config.services and self._config.services[name].enabled:
                try:
                    await service.start()
                except Exception as e:
                    self._logger.error(f"Failed to start service {name}: {e}")

    async def stop_all_services(self) -> None:
        """Stop all services.

        Attempts to stop all registered services regardless of their state.
        Logs errors for failed stops but continues with remaining services.
        """
        for service in self._services.values():
            try:
                await service.stop()
            except Exception as e:
                self._logger.error(f"Failed to stop service {service.name}: {e}")

    def set_state(self, state: ServiceState) -> None:
        """Set the application state.

        Updates the internal state tracking of the application.

        Args:
            state: New application state to set
        """
        self._state = state
