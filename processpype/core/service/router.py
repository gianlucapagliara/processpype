"""Service routing functionality."""

from collections.abc import Callable

from fastapi import APIRouter

from ..models import ServiceStatus


class ServiceRouter(APIRouter):
    """Router for service endpoints."""

    def __init__(self, name: str, get_status: Callable[[], ServiceStatus]) -> None:
        """Initialize the service router.

        Args:
            name: Service name for route prefix
            get_status: Callback to retrieve service status
        """
        super().__init__(prefix=f"/services/{name}")
        self._get_status = get_status
        self._setup_default_routes()

    def _setup_default_routes(self) -> None:
        """Setup default service routes."""

        @self.get("")
        async def get_status() -> ServiceStatus:
            """Get service status."""
            return self._get_status()
