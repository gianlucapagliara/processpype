"""Unit tests for API prefix functionality."""

import logging
from collections.abc import AsyncIterator
from typing import cast

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from processpype.core.application import Application
from processpype.core.configuration.models import ApplicationConfiguration
from processpype.core.models import ServiceState
from processpype.core.service import Service
from processpype.core.service.manager import ServiceManager
from processpype.core.service.router import ServiceRouter


class MockService(Service):
    """Mock service for testing."""

    def __init__(self, name: str = "mock"):
        """Initialize mock service.

        Args:
            name: Service name
        """
        super().__init__(name=name)
        self.status.state = ServiceState.INITIALIZED
        self.status.is_configured = True  # Mock service doesn't need configuration

    def create_manager(self) -> ServiceManager:
        """Create a mock service manager."""
        logger_name = "test.service." + self.name
        return ServiceManager(logging.getLogger(logger_name))

    def create_router(self) -> ServiceRouter:
        """Create a mock service router."""
        return ServiceRouter(
            name=self.name,
            get_status=lambda: self.status,
            start_service=lambda: self.start(),
            stop_service=lambda: self.stop(),
        )

    def requires_configuration(self) -> bool:
        """Check if the service requires configuration."""
        return False

    async def start(self) -> None:
        """Start the mock service."""
        await super().start()
        self.status.state = ServiceState.RUNNING

    async def stop(self) -> None:
        """Stop the mock service."""
        await super().stop()
        self.status.state = ServiceState.STOPPED


@pytest.fixture
def test_config() -> ApplicationConfiguration:
    """Create a test application configuration with API prefix."""
    return ApplicationConfiguration(
        title="Test App",
        version="1.0.0",
        host="localhost",
        port=8080,
        debug=True,
        environment="testing",
        services={},
        api_prefix="/api",
    )


@pytest.fixture
async def application(
    test_config: ApplicationConfiguration,
) -> AsyncIterator[Application]:
    """Create test application instance."""
    app = Application(test_config)
    async with app as application:
        await application.initialize()
        yield application


@pytest.fixture
async def application_with_service(
    application: AsyncIterator[Application],
) -> AsyncIterator[Application]:
    """Create application with registered service."""
    async for app in application:
        app.register_service(MockService)
        yield app


@pytest.mark.asyncio
async def test_main_router_api_prefix(application: AsyncIterator[Application]) -> None:
    """Test that main router endpoints are correctly prefixed with /api."""
    async for app in application:
        client = TestClient(app.api)

        # Test the status endpoint
        response = client.get("/api")
        assert (
            response.status_code == 200
        ), "Status endpoint should be accessible at /api"

        # Test the services listing endpoint
        response = client.get("/api/services")
        assert (
            response.status_code == 200
        ), "Services endpoint should be accessible at /api/services"

        # Test the docs endpoints
        response = client.get("/api/docs")
        assert (
            response.status_code == 200
        ), "Swagger UI should be accessible at /api/docs"

        response = client.get("/api/redoc")
        assert response.status_code == 200, "ReDoc should be accessible at /api/redoc"

        response = client.get("/api/openapi.json")
        assert (
            response.status_code == 200
        ), "OpenAPI schema should be accessible at /api/openapi.json"

        # Verify that the non-prefixed endpoints are not accessible
        response = client.get("/")
        assert (
            response.status_code == 404
        ), "Root endpoint should not be accessible without /api prefix"

        response = client.get("/services")
        assert (
            response.status_code == 404
        ), "Services endpoint should not be accessible without /api prefix"

        response = client.get("/docs")
        assert (
            response.status_code == 404
        ), "Swagger UI should not be accessible without /api prefix"

        response = client.get("/redoc")
        assert (
            response.status_code == 404
        ), "ReDoc should not be accessible without /api prefix"

        response = client.get("/openapi.json")
        assert (
            response.status_code == 404
        ), "OpenAPI schema should not be accessible without /api prefix"


@pytest.mark.asyncio
async def test_service_router_api_prefix(
    application_with_service: AsyncIterator[Application],
) -> None:
    """Test that service router endpoints are correctly prefixed with /api."""
    async for app in application_with_service:
        client = TestClient(app.api)

        # Debug: Print all registered routes
        for route in app.api.routes:
            route = cast(APIRoute, route)
            print(f"  {route.methods} {route.path}")

        # Test the service status endpoint
        response = client.get("/api/services/mock")
        assert (
            response.status_code == 200
        ), "Service status endpoint should be accessible at /api/services/mock"

        # Test the service start endpoint (first stop it to ensure it can be started)
        response = client.post("/api/services/mock/stop")
        assert (
            response.status_code == 200
        ), "Service stop endpoint should be accessible at /api/services/mock/stop"

        response = client.post("/api/services/mock/start")
        assert (
            response.status_code == 200
        ), "Service start endpoint should be accessible at /api/services/mock/start"

        # Test the service stop endpoint
        response = client.post("/api/services/mock/stop")
        assert (
            response.status_code == 200
        ), "Service stop endpoint should be accessible at /api/services/mock/stop"

        # Verify that the non-prefixed endpoints are not accessible
        response = client.get("/services/mock")
        assert (
            response.status_code == 404
        ), "Service status endpoint should not be accessible without /api prefix"

        response = client.post("/services/mock/start")
        assert (
            response.status_code == 404
        ), "Service start endpoint should not be accessible without /api prefix"

        response = client.post("/services/mock/stop")
        assert (
            response.status_code == 404
        ), "Service stop endpoint should not be accessible without /api prefix"
