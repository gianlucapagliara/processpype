"""Core application class for ProcessPype."""

import asyncio

import uvicorn
from fastapi import FastAPI, HTTPException

from .config import ConfigurationManager
from .config.models import ApplicationConfiguration, ServiceConfiguration
from .logfire import get_service_logger, setup_logfire
from .models import ApplicationStatus, ServiceState
from .service import Service
from .system import setup_timezone


class Application:
    """Core application with built-in FastAPI integration."""

    def __init__(self, config: ApplicationConfiguration):
        """Initialize the application.

        Args:
            config: Application configuration
        """
        self._config = config
        self._services: dict[str, Service] = {}
        self._state = ServiceState.STOPPED
        self._initialized = False
        self._setup_complete = False
        self._lock = asyncio.Lock()

    @property
    def config(self) -> ApplicationConfiguration:
        """Get application configuration."""
        return self._config

    @classmethod
    async def create(cls, config_file: str | None = None, **kwargs) -> "Application":
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

    async def initialize(self) -> None:
        """Initialize the application asynchronously."""
        async with self._lock:
            if self._setup_complete:
                return

            # Initialize FastAPI
            self.api = FastAPI(title=self._config.title, version=self._config.version)
            self.setup_core_routes()

            # Setup logging
            setup_logfire(
                self.api,
                token=self._config.logfire_key,
                environment=self._config.environment,
            )
            self.logger = get_service_logger("application")

            self.logger.info(
                "Application initialized",
                extra={
                    "host": self._config.host,
                    "port": self._config.port,
                    "version": self._config.version,
                    "environment": self._config.environment,
                },
            )

            setup_timezone()
            self._setup_complete = True
            self._initialized = True

    def setup_core_routes(self) -> None:
        """Setup core application routes."""

        @self.api.get("/")
        async def get_status() -> ApplicationStatus:
            """Get application status."""
            return ApplicationStatus(
                version=self._config.version,
                state=self._state,
                services={name: svc.status for name, svc in self._services.items()},
            )

        @self.api.get("/services")
        async def list_services() -> dict[str, str]:
            """List all registered services."""
            return {
                name: svc.__class__.__name__ for name, svc in self._services.items()
            }

        @self.api.post("/services/{service_name}/start")
        async def start_service(service_name: str) -> dict[str, str]:
            """Start a service."""
            service = self._services.get(service_name)
            if not service:
                raise HTTPException(
                    status_code=404, detail=f"Service {service_name} not found"
                )

            try:
                await service.start()
                return {"status": "started", "service": service_name}
            except Exception as e:
                service.set_error(str(e))
                raise HTTPException(status_code=500, detail=str(e)) from e

        @self.api.post("/services/{service_name}/stop")
        async def stop_service(service_name: str) -> dict[str, str]:
            """Stop a service."""
            service = self._services.get(service_name)
            if not service:
                raise HTTPException(
                    status_code=404, detail=f"Service {service_name} not found"
                )

            try:
                await service.stop()
                return {"status": "stopped", "service": service_name}
            except Exception as e:
                service.set_error(str(e))
                raise HTTPException(status_code=500, detail=str(e)) from e

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
        if not self._setup_complete:
            raise RuntimeError(
                "Application must be initialized before registering services"
            )

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
        self.api.include_router(service.router)
        self.logger.info(f"Registered service: {service.name}")
        return service

    def get_service(self, name: str) -> Service | None:
        """Get a service by name."""
        return self._services.get(name)

    async def start_service(self, service_name: str) -> None:
        """Start a service by name."""
        if not self._setup_complete:
            raise RuntimeError(
                "Application must be initialized before starting services"
            )

        service = self._services.get(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")
        await service.start()

    async def start(self) -> None:
        """Start the application and API server."""
        if not self._setup_complete:
            await self.initialize()

        self._state = ServiceState.STARTING
        self.logger.info(
            f"Starting application on {self._config.host}:{self._config.port}"
        )

        # Start enabled services
        for name, service in self._services.items():
            if name in self._config.services and self._config.services[name].enabled:
                try:
                    await service.start()
                except Exception as e:
                    self.logger.error(f"Failed to start service {name}: {e}")

        # Start uvicorn server
        config = uvicorn.Config(
            self.api,
            host=self._config.host,
            port=self._config.port,
            log_level="debug" if self._config.debug else "info",
        )
        server = uvicorn.Server(config)

        try:
            self._state = ServiceState.RUNNING
            await server.serve()
        except Exception as e:
            self._state = ServiceState.ERROR
            self.logger.error(f"Failed to start application: {e}")
            raise

    async def stop(self) -> None:
        """Stop the application and all services."""
        if not self._setup_complete:
            return

        self._state = ServiceState.STOPPING
        self.logger.info("Stopping application")

        # Stop all services
        for service in self._services.values():
            try:
                await service.stop()
            except Exception as e:
                self.logger.error(f"Failed to stop service {service.name}: {e}")

        self._state = ServiceState.STOPPED

    async def __aenter__(self) -> "Application":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()
