"""Application-level REST API routing."""

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from processpype.service.models import ApplicationStatus, ServiceState


class ServiceRegistrationRequest(BaseModel):
    service_name: str
    instance_name: str | None = None


class ApplicationRouter(APIRouter):
    """Router for application-level endpoints."""

    def __init__(
        self,
        *,
        get_version: Callable[[], str],
        get_state: Callable[[], ServiceState],
        get_services: Callable[[], dict[str, Any]],
    ) -> None:
        super().__init__()
        self._setup_routes(get_version, get_state, get_services)

    def _setup_routes(
        self,
        get_version: Callable[[], str],
        get_state: Callable[[], ServiceState],
        get_services: Callable[[], dict[str, Any]],
    ) -> None:
        @self.get("/")
        async def get_status() -> dict[str, Any]:
            services = get_services()
            return ApplicationStatus(
                version=get_version(),
                state=get_state(),
                services={name: svc.status for name, svc in services.items()},
            ).model_dump(mode="json")

        @self.get("/services")
        async def get_services_list() -> dict[str, Any]:
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
            return await self._handle_register_service(request)

        @self.delete("/services/{service_name}")
        async def deregister_service(service_name: str) -> dict[str, Any]:
            return await self._handle_deregister_service(service_name)

    async def _handle_register_service(
        self, request: ServiceRegistrationRequest
    ) -> dict[str, Any]:
        try:
            from processpype.application import Application

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
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def _handle_deregister_service(self, service_name: str) -> dict[str, Any]:
        try:
            from processpype.application import Application

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

            return {"status": "deregistered", "service": service_name}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
