"""Service routing functionality."""

from collections.abc import Callable
from typing import Any, cast

from fastapi import APIRouter, HTTPException

from ..models import ServiceStatus


class ServiceRouter(APIRouter):
    """Router for service endpoints."""

    def __init__(
        self,
        name: str,
        get_status: Callable[[], ServiceStatus],
        start_service: Callable[[], Any] | None = None,
        stop_service: Callable[[], Any] | None = None,
        configure_service: Callable[[dict[str, Any]], Any] | None = None,
        configure_and_start_service: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        """Initialize the service router.

        Args:
            name: Service name for route prefix
            get_status: Callback to retrieve service status
            start_service: Callback to start the service
            stop_service: Callback to stop the service
            configure_service: Callback to configure the service
            configure_and_start_service: Callback to configure and start the service
        """
        super().__init__(prefix=f"/services/{name}")
        self._get_status = get_status
        self._start_service = start_service
        self._stop_service = stop_service
        self._configure_service = configure_service
        self._configure_and_start_service = configure_and_start_service
        self._setup_default_routes()

    def _setup_default_routes(self) -> None:
        """Setup default service routes."""

        @self.get("")
        async def get_status() -> dict[str, Any]:
            """Get service status."""
            return self._get_status().model_dump(mode="json")

        if self._start_service:
            self._setup_start_route()

        if self._stop_service:
            self._setup_stop_route()

        if self._configure_service:
            self._setup_configure_route()

        if self._configure_and_start_service:
            self._setup_configure_and_start_route()

    def _setup_start_route(self) -> None:
        """Register the POST /start endpoint."""

        @self.post("/start")
        async def start_service() -> dict[str, str]:
            """Start the service."""
            try:
                start_fn = cast(Callable[[], Any], self._start_service)
                await start_fn()
                return {"status": "started", "service": self.prefix.split("/")[-1]}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e)) from e

    def _setup_stop_route(self) -> None:
        """Register the POST /stop endpoint."""

        @self.post("/stop")
        async def stop_service() -> dict[str, str]:
            """Stop the service."""
            try:
                stop_fn = cast(Callable[[], Any], self._stop_service)
                await stop_fn()
                return {"status": "stopped", "service": self.prefix.split("/")[-1]}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e)) from e

    def _setup_configure_route(self) -> None:
        """Register the POST /configure endpoint."""

        @self.post("/configure")
        async def configure_service(config: dict[str, Any]) -> dict[str, str]:
            """Configure the service."""
            try:
                configure_fn = cast(
                    Callable[[dict[str, Any]], Any], self._configure_service
                )
                configure_fn(config)
                return {
                    "status": "configured",
                    "service": self.prefix.split("/")[-1],
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e)) from e

    def _setup_configure_and_start_route(self) -> None:
        """Register the POST /configure_and_start endpoint."""

        @self.post("/configure_and_start")
        async def configure_and_start_service(
            config: dict[str, Any],
        ) -> dict[str, str]:
            """Configure and start the service."""
            try:
                configure_and_start_fn = cast(
                    Callable[[dict[str, Any]], Any],
                    self._configure_and_start_service,
                )
                await configure_and_start_fn(config)
                return {
                    "status": "configured and started",
                    "service": self.prefix.split("/")[-1],
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e)) from e
