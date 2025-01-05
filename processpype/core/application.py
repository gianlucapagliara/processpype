"""Core application class for ProcessPype."""

import asyncio
from types import TracebackType
from typing import Any

import uvicorn
from fastapi import FastAPI

from processpype.core.manager import ApplicationManager
from processpype.core.system import setup_timezone

from .configuration import ConfigurationManager
from .configuration.models import ApplicationConfiguration
from .logfire import get_service_logger, setup_logfire
from .models import ServiceState
from .router import ApplicationRouter
from .service import Service


class Application:
    """Core application with built-in FastAPI integration."""

    def __init__(self, config: ApplicationConfiguration):
        """Initialize the application.

        Args:
            config: Application configuration
        """
        self._config = config
        self._initialized = False
        self._lock = asyncio.Lock()
        self._manager: ApplicationManager | None = None

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
            self.logger.error(f"Failed to start application: {e}")
            raise

    async def stop(self) -> None:
        """Stop the application and all services."""
        if not self.is_initialized or not self._manager:
            return

        self._manager.set_state(ServiceState.STOPPING)
        self.logger.info("Stopping application")

        # Stop all services
        await self._manager.stop_all_services()
        self._manager.set_state(ServiceState.STOPPED)

    async def __aenter__(self) -> "Application":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.stop()

    # === Initialization ===

    async def initialize(self) -> None:
        """Initialize the application asynchronously."""
        async with self._lock:
            if self.is_initialized:
                return

            setup_timezone()

            # Initialize FastAPI
            self.api = FastAPI(title=self._config.title, version=self._config.version)

            # Setup logging
            setup_logfire(
                self.api,
                token=self._config.logfire_key,
                environment=self._config.environment,
            )
            self.logger = get_service_logger("application")

            # Initialize manager
            self.initialize_manager()

            # Setup core routes
            self.initialize_router()
            self.logger.info(
                "Application initialized",
                extra={
                    "host": self._config.host,
                    "port": self._config.port,
                    "version": self._config.version,
                    "environment": self._config.environment,
                },
            )

            self._initialized = True

    def initialize_manager(self) -> None:
        """Initialize the application manager."""
        self._manager = ApplicationManager(self.logger, self._config)
        self._manager.set_state(ServiceState.INITIALIZED)

    def initialize_router(self) -> None:
        if self._manager is None:
            raise RuntimeError("Application manager not initialized")

        router = ApplicationRouter(
            get_version=lambda: self._config.version,
            get_state=lambda: self._manager.state
            if self._manager
            else ServiceState.STOPPED,
            get_services=lambda: self._manager.services if self._manager else {},
            start_service=self._manager.start_service,
            stop_service=self._manager.stop_service,
        )
        self.api.include_router(router)

    # === Service Management ===

    def register_service(
        self, service_class: type[Service], name: str | None = None
    ) -> Service:
        """Register a new service.

        Args:
            service_class: Service class to register
            name: Optional service name override

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
            self.api.include_router(service.router)

        return service

    def get_service(self, name: str) -> Service | None:
        """Get a service by name."""
        if not self._manager:
            return None
        return self._manager.get_service(name)

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
