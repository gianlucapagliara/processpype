"""Application routing functionality.

This module provides FastAPI router implementation for the ProcessPype application.
It defines REST API endpoints for service management and application status monitoring.
"""

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .models import ApplicationStatus, ServiceState
from .service import Service


class ServiceRegistrationRequest(BaseModel):
    """Service registration request model."""

    service_name: str
    instance_name: str | None = None


class ApplicationRouter(APIRouter):
    """Router for application-level endpoints.

    Provides REST API endpoints for:
    - Application status monitoring
    - Service listing
    - Service registration and deregistration
    """

    def __init__(
        self,
        *,
        get_version: Callable[[], str],
        get_state: Callable[[], ServiceState],
        get_services: Callable[[], dict[str, Service]],
    ) -> None:
        """Initialize the application router.

        Args:
            get_version: Callback to retrieve application version
            get_state: Callback to retrieve current application state
            get_services: Callback to retrieve dictionary of all registered services
        """
        super().__init__()
        self._setup_routes(
            get_version,
            get_state,
            get_services,
        )

    def _setup_routes(
        self,
        get_version: Callable[[], str],
        get_state: Callable[[], ServiceState],
        get_services: Callable[[], dict[str, Service]],
    ) -> None:
        """Setup application routes.

        Configures FastAPI routes for application management:
        - GET /: Application status endpoint
        - GET /services: Service listing endpoint
        - POST /services/register: Service registration endpoint
        - DELETE /services/{service_name}: Service deregistration endpoint

        Args:
            get_version: Callback to retrieve application version
            get_state: Callback to retrieve current application state
            get_services: Callback to retrieve dictionary of all registered services
        """

        @self.get("/")
        async def get_status() -> dict[str, Any]:
            """Get application status.

            Returns:
                ApplicationStatus object containing version, state, and services status
            """
            services = get_services()
            return ApplicationStatus(
                version=get_version(),
                state=get_state(),
                services={name: svc.status for name, svc in services.items()},
            ).model_dump(mode="json")

        @self.get("/services")
        async def get_services_list() -> dict[str, Any]:
            """Get list of registered services.

            Returns:
                Dictionary mapping service names to their status
            """
            services = get_services()
            return {
                "services": [
                    {
                        "name": name,
                        "state": svc.status.state,
                        "is_configured": svc.status.is_configured,
                        "error": svc.status.error,
                    }
                    for name, svc in services.items()
                ]
            }

        @self.post("/services/register")
        async def register_service(
            request: ServiceRegistrationRequest,
        ) -> dict[str, Any]:
            """Register a new service.

            Args:
                request: Service registration request

            Returns:
                Dictionary containing registration status

            Raises:
                HTTPException: If service registration fails
            """
            try:
                # Import here to avoid circular imports
                from processpype.core.application import Application

                # Get the current application instance
                app = Application.get_instance()

                if app is None:
                    raise HTTPException(
                        status_code=500, detail="Application instance not available"
                    )

                service = app.register_service_by_name(
                    request.service_name, request.instance_name
                )

                if service is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Service class '{request.service_name}' not found",
                    )

                return {
                    "status": "registered",
                    "service": service.name,
                    "type": service.__class__.__name__,
                }
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e)) from e

        @self.delete("/services/{service_name}")
        async def deregister_service(service_name: str) -> dict[str, Any]:
            """Deregister a service.

            Args:
                service_name: Name of the service to deregister

            Returns:
                Dictionary containing deregistration status

            Raises:
                HTTPException: If service deregistration fails
            """
            try:
                # Import here to avoid circular imports
                from processpype.core.application import Application

                # Get the current application instance
                app = Application.get_instance()

                if app is None:
                    raise HTTPException(
                        status_code=500, detail="Application instance not available"
                    )

                success = await app.deregister_service(service_name)

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to deregister service '{service_name}'",
                    )

                return {
                    "status": "deregistered",
                    "service": service_name,
                }
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e)) from e
