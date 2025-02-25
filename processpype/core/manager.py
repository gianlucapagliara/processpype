"""Service and lifecycle management for ProcessPype.

This module provides the core application manager responsible for:
- Service registration and configuration
- Service lifecycle management (start/stop)
- Application state tracking
- Error handling and logging
"""

import logging
from typing import Any

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
            name: Optional service name override. If not provided, a unique name will be generated.

        Returns:
            The registered service instance

        Raises:
            ValueError: If service name is already registered
        """
        # Create service instance with the provided name or generate a unique one
        if name is None:
            base_name = service_class.__name__.lower().replace("service", "")
            existing = [s for s in self._services.keys() if s.startswith(base_name)]
            if existing:
                name = f"{base_name}_{len(existing)}"
            else:
                name = base_name

        service = service_class(name)

        if service.name in self._services:
            raise ValueError(f"Service {service.name} already registered")

        # Apply service configuration if available
        if service.name in self._config.services:
            service_config = self._config.services[service.name]
            if hasattr(service, "configure"):
                if not isinstance(service_config, ServiceConfiguration):
                    service_config = ServiceConfiguration.model_validate(service_config)
                service.configure(service_config)

        self._services[service.name] = service
        self._logger.info(f"Registered service: {service.name}")
        return service

    def get_service(self, name: str) -> Service | None:
        """Get a service by name.

        Args:
            name: Service name

        Returns:
            Service instance or None if not found
        """
        return self._services.get(name)

    def get_services_by_type(self, service_type: type[Service]) -> list[Service]:
        """Get all services of a specific type.

        Args:
            service_type: Service class to filter by

        Returns:
            List of service instances of the specified type
        """
        return [s for s in self._services.values() if isinstance(s, service_type)]

    def set_state(self, state: ServiceState) -> None:
        """Set the application state.

        Args:
            state: New application state
        """
        self._logger.info(f"Application state changed: {self._state} -> {state}")
        self._state = state

    async def start_service(self, service_name: str) -> None:
        """Start a service by name.

        Args:
            service_name: Name of the service to start

        Raises:
            ValueError: If service is not found
            ConfigurationError: If service is not properly configured
            Exception: If service fails to start
        """
        service = self.get_service(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")

        self._logger.info(f"Starting service: {service_name}")
        await service.start()

    async def stop_service(self, service_name: str) -> None:
        """Stop a service by name.

        Args:
            service_name: Name of the service to stop

        Raises:
            ValueError: If service is not found
            Exception: If service fails to stop
        """
        service = self.get_service(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")

        self._logger.info(f"Stopping service: {service_name}")
        await service.stop()

    def configure_service(self, service_name: str, config: dict[str, Any]) -> None:
        """Configure a service by name.

        Args:
            service_name: Name of the service to configure
            config: Service configuration

        Raises:
            ValueError: If service is not found
            ConfigurationError: If configuration is invalid
        """
        service = self.get_service(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")

        self._logger.info(f"Configuring service: {service_name}")
        service.configure(config)

    async def configure_and_start_service(
        self, service_name: str, config: dict[str, Any]
    ) -> None:
        """Configure and start a service by name.

        Args:
            service_name: Name of the service to configure and start
            config: Service configuration

        Raises:
            ValueError: If service is not found
            ConfigurationError: If configuration is invalid
            Exception: If service fails to start
        """
        service = self.get_service(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")

        self._logger.info(f"Configuring and starting service: {service_name}")
        await service.configure_and_start(config)

    async def start_enabled_services(self) -> None:
        """Start all enabled services.

        This method starts all services that are enabled in the configuration.
        """
        for service_name, service in self._services.items():
            # Skip services that are not enabled
            if service_name in self._config.services:
                service_config = self._config.services[service_name]
                if isinstance(service_config, dict) and not service_config.get(
                    "enabled", True
                ):
                    self._logger.info(f"Skipping disabled service: {service_name}")
                    continue
                elif (
                    isinstance(service_config, ServiceConfiguration)
                    and not service_config.enabled
                ):
                    self._logger.info(f"Skipping disabled service: {service_name}")
                    continue

            # Start the service if it's configured or doesn't require configuration
            if service.status.is_configured or not service.requires_configuration():
                self._logger.info(f"Starting enabled service: {service_name}")
                try:
                    await service.start()
                except Exception as e:
                    self._logger.error(
                        f"Failed to start service {service_name}: {e}", exc_info=True
                    )
                    service.set_error(str(e))

    async def stop_all_services(self) -> None:
        """Stop all running services."""
        for service_name, service in self._services.items():
            if service.status.state in (ServiceState.RUNNING, ServiceState.STARTING):
                self._logger.info(f"Stopping service: {service_name}")
                try:
                    await service.stop()
                except Exception as e:
                    self._logger.error(
                        f"Failed to stop service {service_name}: {e}", exc_info=True
                    )
                    service.set_error(str(e))
