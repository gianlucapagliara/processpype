"""Application entry point factory."""

import os
import signal
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from processpype.application import Application
from processpype.config.models import ProcessPypeConfig
from processpype.service.registry import get_available_services


class ApplicationCreator:
    """Singleton factory for creating and managing the Application instance."""

    is_shutting_down = False
    app: Application | None = None

    @classmethod
    def get_application(
        cls,
        config: ProcessPypeConfig | None = None,
        application_class: type[Application] = Application,
    ) -> Application:
        if cls.app is not None:
            return cls.app

        config = config or ProcessPypeConfig()
        cls.app = application_class(config)
        cls._setup_lifespan()
        return cls.app

    @classmethod
    def _setup_lifespan(cls) -> None:
        app = cls.app
        if app is None:
            raise RuntimeError("Application not initialized")

        cls._install_signal_handlers(app)

        @asynccontextmanager
        async def lifespan(_fastapi_app: FastAPI) -> AsyncIterator[None]:
            await app.initialize()
            await cls._start_enabled_services(app)
            yield
            if not cls.is_shutting_down:
                cls.is_shutting_down = True
                app.logger.warning("FastAPI shutdown event triggered")
                await app.stop()
                app.logger.warning("Application shutdown complete")

        app.api.router.lifespan_context = lifespan

    @staticmethod
    def _install_signal_handlers(app: Application) -> None:
        def _signal_handler(sig_num: int, _: Any) -> None:
            sig = signal.Signals(sig_num)
            app.logger.warning(
                f"Received signal {sig.name}, initiating graceful shutdown..."
            )
            sys.exit(0)

        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, _signal_handler)
        app.logger.info(
            "Signal handlers configured for graceful shutdown (SIGTERM, SIGINT)"
        )

    @staticmethod
    async def _start_enabled_services(app: Application) -> None:
        services_to_enable = os.getenv("ENABLED_SERVICES", "").split(",")
        available = get_available_services()
        for service_name in services_to_enable:
            service_name = service_name.strip()
            if not service_name:
                continue
            if service_name not in available:
                app.logger.warning(f"Service {service_name} not found")
                continue
            try:
                app.register_service(available[service_name], name=service_name)
                await app.start_service(service_name)
                app.logger.info(f"Service {service_name} registered and started")
            except Exception as e:
                app.logger.error(f"Failed to start service {service_name}: {e}")
