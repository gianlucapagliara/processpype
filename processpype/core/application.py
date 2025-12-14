"""Core application class for ProcessPype."""

import asyncio
import logging
from types import TracebackType
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI

from processpype.core.manager import ApplicationManager
from processpype.core.system import setup_timezone

from .configuration import ConfigurationManager
from .configuration.models import ApplicationConfiguration
from .logfire import get_service_logger, instrument_fastapi, setup_logfire
from .models import ServiceState
from .router import ApplicationRouter
from .service import Service


class Application:
    """Core application with built-in FastAPI integration."""

    # Class variable to store the singleton instance
    _instance: Optional["Application"] = None

    def __init__(self, config: ApplicationConfiguration):
        """Initialize the application.

        Args:
            config: Application configuration
        """
        self._config = config
        self._initialized = False
        self._lock = asyncio.Lock()
        self._manager: ApplicationManager | None = None
        self._api = self.create_api()

        # Set the singleton instance
        Application._instance = self

    @classmethod
    def get_instance(cls) -> Optional["Application"]:
        """Get the singleton application instance.

        Returns:
            The application instance or None if not initialized
        """
        return cls._instance

    @classmethod
    async def create(
        cls, config_file: str | None = None, **kwargs: Any
    ) -> "Application":
        """Create application instance with configuration from file and/or kwargs.

        Args:
            config_file: Optional path to configuration file
            **kwargs: Configuration overrides

        Returns:
            Application instance
        """
        config = await ConfigurationManager.load_application_config(
            config_file=config_file, **kwargs
        )
        return cls(config)

    # === Properties ===

    @property
    def api(self) -> FastAPI:
        """Get the FastAPI instance."""
        return self._api

    @property
    def is_initialized(self) -> bool:
        """Check if the application is initialized."""
        return self._initialized

    @property
    def config(self) -> ApplicationConfiguration:
        """Get application configuration."""
        return self._config

    # === Lifecycle ===

    async def start(self) -> None:
        """Start the application and API server."""
        if not self.is_initialized:
            await self.initialize()

        if not self._manager:
            raise RuntimeError("Application manager not initialized")

        self._manager.set_state(ServiceState.STARTING)
        self.logger.info(
            f"Starting application on {self._config.host}:{self._config.port}"
        )

        # Start enabled services
        await self._manager.start_enabled_services()

        # Start uvicorn server
        config = uvicorn.Config(
            self.api,
            host=self._config.host,
            port=self._config.port,
            log_level="debug" if self._config.debug else "info",
        )
        server = uvicorn.Server(config)

        try:
            self._manager.set_state(ServiceState.RUNNING)
            await server.serve()
        except Exception as e:
            self._manager.set_state(ServiceState.ERROR)
            self.logger.error(f"Application error: {e}")
            raise
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the application and all services."""
        if not self._manager:
            return

        self._manager.set_state(ServiceState.STOPPING)
        self.logger.info("Stopping application")

        # Stop all services
        await self._manager.stop_all_services()

        # Wait for all services to be stopped with a timeout
        timeout = self._config.closing_timeout_seconds
        start_time = asyncio.get_event_loop().time()

        while True:
            # Check if all services are stopped
            unstopped_services = [
                service
                for service in self._manager.services.values()
                if service.status.state != ServiceState.STOPPED
            ]

            if not unstopped_services:
                break

            # Check if we've exceeded the timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                self.logger.warning(
                    "Timeout waiting for services to stop. Some services may not have stopped properly."
                )
                break
            else:
                self.logger.info(
                    f"Waiting for {len(unstopped_services)} services to stop..."
                )

            # Wait a bit before checking again
            await asyncio.sleep(1)

        self._manager.set_state(ServiceState.STOPPED)

    async def __aenter__(self) -> "Application":
        """Enter async context manager."""
        if not self.is_initialized:
            await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        await self.stop()

    # === Initialization ===

    async def initialize(self) -> None:
        """Initialize the application.

        This method sets up logging, timezone, and creates the application manager.
        """
        async with self._lock:
            if self._initialized:
                return

            # Setup timezone
            setup_timezone()

            # Setup logging
            self.logger.info("Initializing application")
            if self._config.logfire_key:
                self.logger.info(
                    f"Setting up Logfire with environment: {self._config.environment} and app name: {self._config.title}"
                )
                setup_logfire(
                    token=self._config.logfire_key,
                    environment=self._config.environment,
                    app_name=self._config.title,
                )
                instrument_fastapi(self.api)

            # Create application manager
            self._manager = ApplicationManager(self.logger, self._config)

            # Setup API routes
            self._setup_api_routes()

            self._initialized = True
            self.logger.info("Application initialized")

    @property
    def logger(self) -> logging.Logger:
        """Get the application logger."""
        return get_service_logger("app")

    def create_api(self) -> FastAPI:
        """Create the FastAPI instance."""
        return FastAPI(
            title=self._config.title,
            version=self._config.version,
            debug=self._config.debug,
            docs_url=f"{self._config.api_prefix}/docs"
            if self._config.api_prefix
            else "/docs",
            redoc_url=f"{self._config.api_prefix}/redoc"
            if self._config.api_prefix
            else "/redoc",
            openapi_url=f"{self._config.api_prefix}/openapi.json"
            if self._config.api_prefix
            else "/openapi.json",
        )

    def _setup_api_routes(self) -> None:
        """Setup API routes."""
        if self._manager is None:
            raise RuntimeError("Application manager not initialized")

        router = ApplicationRouter(
            get_version=lambda: self._config.version,
            get_state=lambda: self._manager.state
            if self._manager
            else ServiceState.STOPPED,
            get_services=lambda: self._manager.services if self._manager else {},
        )
        self.api.include_router(router, prefix=self._config.api_prefix)

    # === Service Management ===

    def register_service(
        self, service_class: type[Service], name: str | None = None
    ) -> Service:
        """Register a new service.

        Args:
            service_class: Service class to register
            name: Optional service name override. If not provided, a unique name will be generated.

        Returns:
            The registered service instance

        Raises:
            RuntimeError: If application is not initialized
            ValueError: If service name is already registered
        """
        if not self.is_initialized or not self._manager:
            raise RuntimeError(
                "Application must be initialized before registering services"
            )

        service = self._manager.register_service(service_class, name)
        if service.router:
            self.api.include_router(service.router, prefix=self._config.api_prefix)

        return service

    def register_service_by_name(
        self, service_name: str, instance_name: str | None = None
    ) -> Service | None:
        """Register a service by its registered name.

        This method looks up a service class in the service registry and registers
        an instance of it with the application.

        Args:
            service_name: Name of the service class to register (without 'service' suffix)
            instance_name: Optional instance name override

        Returns:
            The registered service instance or None if service class not found

        Raises:
            RuntimeError: If application is not initialized
            ValueError: If service name is already registered
        """
        try:
            # Import here to avoid circular imports
            from processpype.services import get_service_class

            service_class = get_service_class(service_name)
            if service_class is None:
                self.logger.warning(
                    f"Service class '{service_name}' not found in registry"
                )
                return None

            return self.register_service(service_class, instance_name)
        except ImportError:
            self.logger.error("Failed to import service registry")
            return None

    async def deregister_service(self, service_name: str) -> bool:
        """Deregister a service by name.

        This method stops the service if it's running and removes it from the application.

        Args:
            service_name: Name of the service to deregister

        Returns:
            True if the service was deregistered, False otherwise

        Raises:
            ValueError: If service is not found
        """
        if not self.is_initialized or not self._manager:
            raise RuntimeError(
                "Application must be initialized before deregistering services"
            )

        service = self._manager.get_service(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")

        # Stop the service if it's running
        if service.status.state in (ServiceState.RUNNING, ServiceState.STARTING):
            await self._manager.stop_service(service_name)

        # Note: FastAPI doesn't provide a clean way to remove routers once added
        # In a production environment, you would need to recreate the FastAPI app
        # or use a more sophisticated approach to manage routes
        self.logger.warning(
            "Service router cannot be fully removed from FastAPI. "
            "Routes will remain but service will be unavailable."
        )

        # Remove the service from the manager
        if self._manager and service_name in self._manager.services:
            del self._manager.services[service_name]
            self.logger.info(f"Deregistered service: {service_name}")
            return True

        return False

    def get_service(self, name: str) -> Service | None:
        """Get a service by name."""
        if not self._manager:
            return None
        return self._manager.get_service(name)

    def get_services_by_type(self, service_type: type[Service]) -> list[Service]:
        """Get all services of a specific type."""
        if not self._manager:
            return []
        return self._manager.get_services_by_type(service_type)

    async def start_service(self, service_name: str) -> None:
        """Start a service by name."""
        if not self.is_initialized or not self._manager:
            raise RuntimeError(
                "Application must be initialized before starting services"
            )
        await self._manager.start_service(service_name)

    async def stop_service(self, service_name: str) -> None:
        """Stop a service by name."""
        if not self._manager:
            return
        await self._manager.stop_service(service_name)
