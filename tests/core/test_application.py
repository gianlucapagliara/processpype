"""Unit tests for core application."""

import logging
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from fastapi import FastAPI

from processpype.core.application import Application
from processpype.core.configuration.models import ApplicationConfiguration
from processpype.core.models import ServiceState
from processpype.core.service import Service
from processpype.core.service.manager import ServiceManager
from processpype.core.service.router import ServiceRouter


@pytest.fixture
def app_config() -> ApplicationConfiguration:
    """Create test application configuration."""
    return ApplicationConfiguration(
        title="Test App",
        version="1.0.0",
        host="localhost",
        port=8080,
        debug=True,
        environment="testing",
    )


@pytest.fixture
async def app(
    app_config: ApplicationConfiguration,
) -> AsyncGenerator[Application, None]:
    """Create test application instance."""
    app = Application(app_config)
    async with app as application:
        yield application


class MockService(Service):
    """Mock service for testing."""

    def __init__(self, name: str | None = None):
        super().__init__(name)
        self.start_called = False
        self.stop_called = False

    async def start(self) -> None:
        """Start the mock service."""
        self.start_called = True
        self.status.state = ServiceState.RUNNING

    async def stop(self) -> None:
        """Stop the mock service."""
        self.stop_called = True
        self.status.state = ServiceState.STOPPED

    def create_manager(self) -> ServiceManager:
        """Create a mock service manager."""
        return ServiceManager(logging.getLogger(f"test.service.{self.name}"))

    def create_router(self) -> ServiceRouter | None:
        """Create a mock service router."""
        return ServiceRouter(
            name=self.name,
            get_status=lambda: self.status,
        )


@pytest.mark.asyncio
async def test_application_creation(app_config: ApplicationConfiguration) -> None:
    """Test application creation."""
    app = Application(app_config)
    assert app.config == app_config
    assert not app.is_initialized


@pytest.mark.asyncio
async def test_application_create_from_config() -> None:
    """Test application creation from config file."""
    with patch(
        "processpype.core.configuration.ConfigurationManager.load_application_config"
    ) as mock_load:
        mock_load.return_value = ApplicationConfiguration(
            title="Test App",
            version="1.0.0",
            host="localhost",
            port=8080,
            debug=True,
            environment="testing",
        )

        app = await Application.create(config_file="test.yaml")
        assert app.config.title == "Test App"
        assert app.config.version == "1.0.0"
        mock_load.assert_called_once_with(config_file="test.yaml")


@pytest.mark.asyncio
async def test_application_initialization(
    app: AsyncGenerator[Application, None],
) -> None:
    """Test application initialization."""
    async for application in app:
        await application.initialize()
        assert application.is_initialized
        assert isinstance(application.api, FastAPI)
        assert application._manager is not None


@pytest.mark.asyncio
async def test_application_double_initialization(
    app: AsyncGenerator[Application, None],
) -> None:
    """Test that double initialization is safe."""
    async for application in app:
        await application.initialize()
        initial_manager = application._manager

        await application.initialize()
        assert application._manager == initial_manager


@pytest.mark.asyncio
async def test_application_start_stop(app: AsyncGenerator[Application, None]) -> None:
    """Test application start and stop."""
    async for application in app:
        await application.initialize()  # Ensure manager is initialized
        with patch("uvicorn.Server.serve") as mock_serve:
            mock_serve.return_value = None

            await application.start()
            assert application._manager is not None
            assert application._manager.state == ServiceState.RUNNING
            mock_serve.assert_called_once()

            await application.stop()
            assert application._manager.state == ServiceState.STOPPED


@pytest.mark.asyncio
async def test_service_registration(app: AsyncGenerator[Application, None]) -> None:
    """Test service registration."""
    async for application in app:
        await application.initialize()

        service = application.register_service(MockService)
        assert service is not None
        assert isinstance(service, MockService)
        assert service.name in application._manager.services


@pytest.mark.asyncio
async def test_service_registration_before_init(
    app_config: ApplicationConfiguration,
) -> None:
    """Test service registration before initialization."""
    app = Application(app_config)

    with pytest.raises(RuntimeError):
        app.register_service(MockService)


@pytest.mark.asyncio
async def test_service_lifecycle(app: AsyncGenerator[Application, None]) -> None:
    """Test service lifecycle management."""
    async for application in app:
        await application.initialize()

        # Register and start service
        service = application.register_service(MockService)
        await application.start_service(service.name)
        assert service.status.state == ServiceState.RUNNING
        assert service.start_called

        # Stop service
        await application.stop_service(service.name)
        assert service.status.state == ServiceState.STOPPED
        assert service.stop_called


@pytest.mark.asyncio
async def test_get_service(app: AsyncGenerator[Application, None]) -> None:
    """Test service retrieval."""
    async for application in app:
        await application.initialize()

        service = application.register_service(MockService, name="test_service")
        retrieved = application.get_service("test_service")
        assert retrieved == service

        assert application.get_service("nonexistent") is None


@pytest.mark.asyncio
async def test_application_context_manager(
    app_config: ApplicationConfiguration,
) -> None:
    """Test application as async context manager."""
    app = Application(app_config)

    async with app as context:
        assert context.is_initialized
        assert isinstance(context.api, FastAPI)
        assert context._manager is not None
        assert context._manager.state == ServiceState.INITIALIZED

    assert context._manager.state == ServiceState.STOPPED


@pytest.mark.asyncio
async def test_application_error_handling(
    app: AsyncGenerator[Application, None],
) -> None:
    """Test application error handling during start."""
    async for application in app:
        await application.initialize()  # Ensure manager is initialized
        with patch("uvicorn.Server.serve") as mock_serve:
            mock_serve.side_effect = Exception("Server error")

            with pytest.raises(Exception):
                await application.start()

            assert application._manager is not None
            assert application._manager.state == ServiceState.ERROR
