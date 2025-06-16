"""Main application entry point with service management."""

import os
import signal
import sys
from typing import Any

from processpype.core.application import Application
from processpype.core.configuration.models import ApplicationConfiguration
from processpype.services import get_available_services


class ApplicationCreator:
    is_shutting_down = False
    app: Application | None = None

    @staticmethod
    def get_env_config() -> dict[str, Any]:
        """Get configuration from environment variables."""
        return {
            "title": os.getenv("APP_TITLE", "Trading Application"),
            "host": os.getenv("APP_HOST", "0.0.0.0"),
            "port": int(os.getenv("APP_PORT", "8000")),
            "debug": os.getenv("APP_DEBUG", "false").lower() == "true",
            "environment": os.getenv("APP_ENV", "production"),
            "logfire_key": os.getenv("LOGFIRE_KEY"),
            "api_prefix": os.getenv("API_PREFIX", ""),
        }

    @classmethod
    def get_application(
        cls,
        config: ApplicationConfiguration | None = None,
        application_class: type[Application] = Application,
    ) -> Application:
        """Create the application instance."""
        if cls.app is not None:
            return cls.app

        config = config or ApplicationConfiguration(**cls.get_env_config())
        cls.app = application_class(config)
        cls._setup_startup_callback()
        cls._setup_shutdown_callback()
        return cls.app

    @classmethod
    def _setup_startup_callback(cls) -> None:
        app = cls.app
        if app is None:
            raise RuntimeError("Application not initialized")

        def handle_signals() -> None:
            """Setup signal handlers for graceful shutdown."""

            def _signal_handler(sig_num: int, _: Any) -> None:
                """Handle shutdown signals by triggering graceful shutdown."""
                # Convert signal number to enum for logging
                sig = signal.Signals(sig_num)
                app.logger.warning(
                    f"Received signal {sig.name}, initiating graceful shutdown..."
                )
                app.logger.warning("Triggering Uvicorn shutdown...")

                # Exit with appropriate status code
                # This will trigger uvicorn's graceful shutdown
                sys.exit(0)

            # Handle SIGTERM (docker stop) and SIGINT (Ctrl+C)
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, _signal_handler)
            app.logger.info(
                "Signal handlers configured for graceful shutdown (SIGTERM, SIGINT)"
            )

        @app.api.on_event("startup")
        async def startup_event() -> None:
            """Initialize the application and services on startup."""
            # Initialize the application first to set up logging
            await app.initialize()

            # Setup signal handlers
            handle_signals()
            app.logger.info("Signal handlers configured for graceful shutdown")

            # Start enabled services
            services_to_enable = os.getenv("ENABLED_SERVICES", "").split(",")
            for service_name in services_to_enable:
                service_name = service_name.strip()
                if service_name == "":
                    continue

                if service_name not in get_available_services():
                    app.logger.warning(f"Service {service_name} not found")
                    continue

                try:
                    app.register_service(
                        get_available_services()[service_name], name=service_name
                    )
                    await app.start_service(service_name)
                    app.logger.info(f"Service {service_name} registered and started")
                except Exception as e:
                    app.logger.error(f"Failed to start service {service_name}: {e}")

    @classmethod
    def _setup_shutdown_callback(cls) -> None:  # noqa: C901
        app = cls.app
        if app is None:
            raise RuntimeError("Application not initialized")

        @app.api.on_event("shutdown")
        async def shutdown_event() -> None:
            """Stop the application on shutdown."""
            if not cls.is_shutting_down:
                cls.is_shutting_down = True
                app.logger.warning("FastAPI shutdown event triggered")
                app.logger.warning("Stopping application...")
                await app.stop()
                app.logger.warning("Application shutdown complete")
