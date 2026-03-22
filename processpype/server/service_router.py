"""Per-service REST API routing."""

from collections.abc import Callable
from typing import Any, cast

from fastapi import APIRouter, HTTPException

from processpype.service.models import ServiceStatus


class ServiceRouter(APIRouter):
    """Router providing lifecycle endpoints for a single service."""

    def __init__(
        self,
        name: str,
        get_status: Callable[[], ServiceStatus],
        start_service: Callable[[], Any] | None = None,
        stop_service: Callable[[], Any] | None = None,
        configure_service: Callable[[dict[str, Any]], Any] | None = None,
        configure_and_start_service: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        super().__init__(prefix=f"/services/{name}")
        self._get_status = get_status
        self._start_service = start_service
        self._stop_service = stop_service
        self._configure_service = configure_service
        self._configure_and_start_service = configure_and_start_service
        self._setup_default_routes()

    def _setup_default_routes(self) -> None:
        @self.get("")
        async def get_status() -> dict[str, Any]:
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
        @self.post("/start")
        async def start_service() -> dict[str, str]:
            try:
                start_fn = cast(Callable[[], Any], self._start_service)
                await start_fn()
                return {"status": "started", "service": self.prefix.split("/")[-1]}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e)) from e

    def _setup_stop_route(self) -> None:
        @self.post("/stop")
        async def stop_service() -> dict[str, str]:
            try:
                stop_fn = cast(Callable[[], Any], self._stop_service)
                await stop_fn()
                return {"status": "stopped", "service": self.prefix.split("/")[-1]}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e)) from e

    def _setup_configure_route(self) -> None:
        @self.post("/configure")
        async def configure_service(config: dict[str, Any]) -> dict[str, str]:
            try:
                configure_fn = cast(
                    Callable[[dict[str, Any]], Any], self._configure_service
                )
                configure_fn(config)
                return {"status": "configured", "service": self.prefix.split("/")[-1]}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e)) from e

    def _setup_configure_and_start_route(self) -> None:
        @self.post("/configure_and_start")
        async def configure_and_start_service(
            config: dict[str, Any],
        ) -> dict[str, str]:
            try:
                fn = cast(
                    Callable[[dict[str, Any]], Any],
                    self._configure_and_start_service,
                )
                await fn(config)
                return {
                    "status": "configured and started",
                    "service": self.prefix.split("/")[-1],
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e)) from e
