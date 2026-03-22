"""Core application class for ProcessPype."""

import asyncio
import logging
from types import TracebackType
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI

from processpype.app_manager import ApplicationManager
from processpype.config import load_config
from processpype.config.models import ProcessPypeConfig
from processpype.environment import setup_environment
from processpype.server.app_router import ApplicationRouter
from processpype.service.base import Service
from processpype.service.models import ServiceState


class Application:
    """Core application with built-in FastAPI integration.

    v2 initialization flow:
    1. Load ProcessPypeConfig from YAML
    2. Setup environment (timezone, project dir, run ID)
    3. Init observability (logging + tracing) — Phase 2
    4. Init notifications — Phase 3
    5. Create FastAPI server and wire routes
    6. Create ApplicationManager and register services
    """

    _instance: Optional["Application"] = None

    def __init__(self, config: ProcessPypeConfig) -> None:
        self._config = config
        self._initialized = False
        self._lock = asyncio.Lock()
        self._manager: ApplicationManager | None = None
        self._api = self._create_api()
        Application._instance = self

    @classmethod
    def get_instance(cls) -> Optional["Application"]:
        return cls._instance

    @classmethod
    async def create(
        cls, config_file: str | None = None, **kwargs: Any
    ) -> "Application":
        config = await load_config(config_file, **kwargs)
        return cls(config)

    # === Properties ===

    @property
    def api(self) -> FastAPI:
        return self._api

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def config(self) -> ProcessPypeConfig:
        return self._config

    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger("processpype.app")

    # === Lifecycle ===

    async def start(self) -> None:
        if not self.is_initialized:
            await self.initialize()

        if not self._manager:
            raise RuntimeError("Application manager not initialized")

        self._manager.set_state(ServiceState.STARTING)
        self.logger.info(
            f"Starting application on {self._config.server.host}:{self._config.server.port}"
        )

        await self._manager.start_enabled_services()

        config = uvicorn.Config(
            self.api,
            host=self._config.server.host,
            port=self._config.server.port,
            log_level="debug" if self._config.app.debug else "info",
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
        if not self._manager:
            return

        self._manager.set_state(ServiceState.STOPPING)
        self.logger.info("Stopping application")

        await self._manager.stop_all_services()

        timeout = self._config.server.closing_timeout_seconds
        start_time = asyncio.get_event_loop().time()

        while True:
            unstopped = [
                s
                for s in self._manager.services.values()
                if s.status.state != ServiceState.STOPPED
            ]
            if not unstopped:
                break
            if asyncio.get_event_loop().time() - start_time > timeout:
                self.logger.warning(
                    "Timeout waiting for services to stop. Some services may not have stopped properly."
                )
                break
            else:
                self.logger.info(f"Waiting for {len(unstopped)} services to stop...")
            await asyncio.sleep(1)

        self._manager.set_state(ServiceState.STOPPED)

    async def __aenter__(self) -> "Application":
        if not self.is_initialized:
            await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.stop()

    # === Initialization ===

    async def initialize(self) -> None:
        async with self._lock:
            if self._initialized:
                return

            # 1. Environment
            setup_environment(self._config.app)

            # 2. Observability
            from processpype.observability.setup import init_observability

            init_observability(self._config.observability)
            self.logger.info("Initializing application")

            # 3. Notifications
            # (Notification handlers are registered by consuming services,
            #  not auto-initialized here. The config is available at
            #  self._config.notifications for consumers to use.)

            # 4. Application manager + routes
            self._manager = ApplicationManager(self.logger, self._config)
            self._setup_api_routes()

            self._initialized = True
            self.logger.info("Application initialized")

    def _create_api(self) -> FastAPI:
        prefix = self._config.server.api_prefix
        return FastAPI(
            title=self._config.app.title,
            version=self._config.app.version,
            debug=self._config.app.debug,
            docs_url=f"{prefix}/docs" if prefix else "/docs",
            redoc_url=f"{prefix}/redoc" if prefix else "/redoc",
            openapi_url=f"{prefix}/openapi.json" if prefix else "/openapi.json",
        )

    def _setup_api_routes(self) -> None:
        if self._manager is None:
            raise RuntimeError("Application manager not initialized")

        router = ApplicationRouter(
            get_version=lambda: self._config.app.version,
            get_state=lambda: (
                self._manager.state if self._manager else ServiceState.STOPPED
            ),
            get_services=lambda: self._manager.services if self._manager else {},
        )
        self.api.include_router(router, prefix=self._config.server.api_prefix)

    # === Service Management ===

    def register_service(
        self, service_class: type[Service], name: str | None = None
    ) -> Service:
        if not self.is_initialized or not self._manager:
            raise RuntimeError(
                "Application must be initialized before registering services"
            )

        service = self._manager.register_service(service_class, name)
        if service.router:
            self.api.include_router(
                service.router, prefix=self._config.server.api_prefix
            )
        return service

    def register_service_by_name(
        self, service_name: str, instance_name: str | None = None
    ) -> Service | None:
        try:
            from processpype.service.registry import get_service_class

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
        if not self.is_initialized or not self._manager:
            raise RuntimeError(
                "Application must be initialized before deregistering services"
            )

        service = self._manager.get_service(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")

        if service.status.state in (ServiceState.RUNNING, ServiceState.STARTING):
            await self._manager.stop_service(service_name)

        self.logger.warning(
            "Service router cannot be fully removed from FastAPI. "
            "Routes will remain but service will be unavailable."
        )

        if self._manager and service_name in self._manager.services:
            del self._manager.services[service_name]
            self.logger.info(f"Deregistered service: {service_name}")
            return True
        return False

    def get_service(self, name: str) -> Service | None:
        if not self._manager:
            return None
        return self._manager.get_service(name)

    def get_services_by_type(self, service_type: type[Service]) -> list[Service]:
        if not self._manager:
            return []
        return self._manager.get_services_by_type(service_type)

    async def start_service(self, service_name: str) -> None:
        if not self.is_initialized or not self._manager:
            raise RuntimeError(
                "Application must be initialized before starting services"
            )
        await self._manager.start_service(service_name)

    async def stop_service(self, service_name: str) -> None:
        if not self._manager:
            return
        await self._manager.stop_service(service_name)
