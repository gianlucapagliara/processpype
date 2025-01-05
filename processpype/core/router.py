"""Application routing functionality.

This module provides FastAPI router implementation for the ProcessPype application.
It defines REST API endpoints for service management and application status monitoring.
"""

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException

from .models import ApplicationStatus, ServiceState
from .service.service import Service


class ApplicationRouter(APIRouter):
    """Router for application-level endpoints.

    Provides REST API endpoints for:
    - Application status monitoring
    - Service listing
    - Service lifecycle management (start/stop)
    """

    def __init__(
        self,
        *,
        get_version: Callable[[], str],
        get_state: Callable[[], ServiceState],
        get_services: Callable[[], dict[str, Service]],
        start_service: Callable[[str], Any],
        stop_service: Callable[[str], Any],
    ) -> None:
        """Initialize the application router.

        Args:
            get_version: Callback to retrieve application version
            get_state: Callback to retrieve current application state
            get_services: Callback to retrieve dictionary of all registered services
            start_service: Callback to initiate service startup
            stop_service: Callback to initiate service shutdown
        """
        super().__init__()
        self._setup_routes(
            get_version, get_state, get_services, start_service, stop_service
        )

    def _setup_routes(
        self,
        get_version: Callable[[], str],
        get_state: Callable[[], ServiceState],
        get_services: Callable[[], dict[str, Service]],
        start_service: Callable[[str], Any],
        stop_service: Callable[[str], Any],
    ) -> None:
        """Setup application routes.

        Configures FastAPI routes for application management:
        - GET /: Application status endpoint
        - GET /services: Service listing endpoint
        - POST /services/{service_name}/start: Service start endpoint
        - POST /services/{service_name}/stop: Service stop endpoint

        Args:
            get_version: Callback to retrieve application version
            get_state: Callback to retrieve current application state
            get_services: Callback to retrieve dictionary of all registered services
            start_service: Callback to initiate service startup
            stop_service: Callback to initiate service shutdown
        """

        @self.get("/")
        async def get_status() -> ApplicationStatus:
            """Get application status.

            Returns:
                ApplicationStatus object containing version, state, and services status
            """
            services = get_services()
            return ApplicationStatus(
                version=get_version(),
                state=get_state(),
                services={name: svc.status for name, svc in services.items()},
            )

        @self.get("/services")
        async def list_services() -> dict[str, str]:
            """List all registered services.

            Returns:
                Dictionary mapping service names to their class names
            """
            services = get_services()
            return {name: svc.__class__.__name__ for name, svc in services.items()}

        @self.post("/services/{service_name}/start")
        async def start_service_route(service_name: str) -> dict[str, str]:
            """Start a service.

            Args:
                service_name: Name of the service to start

            Returns:
                Dictionary containing status confirmation

            Raises:
                HTTPException: If service not found or start operation fails
            """
            services = get_services()
            service = services.get(service_name)
            if not service:
                raise HTTPException(
                    status_code=404, detail=f"Service {service_name} not found"
                )

            try:
                await start_service(service_name)
                return {"status": "started", "service": service_name}
            except Exception as e:
                service.set_error(str(e))
                raise HTTPException(status_code=500, detail=str(e)) from e

        @self.post("/services/{service_name}/stop")
        async def stop_service_route(service_name: str) -> dict[str, str]:
            """Stop a service.

            Args:
                service_name: Name of the service to stop

            Returns:
                Dictionary containing status confirmation

            Raises:
                HTTPException: If service not found or stop operation fails
            """
            services = get_services()
            service = services.get(service_name)
            if not service:
                raise HTTPException(
                    status_code=404, detail=f"Service {service_name} not found"
                )

            try:
                await stop_service(service_name)
                return {"status": "stopped", "service": service_name}
            except Exception as e:
                service.set_error(str(e))
                raise HTTPException(status_code=500, detail=str(e)) from e
