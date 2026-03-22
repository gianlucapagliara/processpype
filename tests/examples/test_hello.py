"""Tests for the HelloService example."""

import pytest

from processpype.examples.hello import HelloService
from processpype.service.models import ServiceState


class TestHelloService:
    def test_create(self) -> None:
        service = HelloService()
        assert service.name == "hello"
        assert service.status.state == ServiceState.INITIALIZED

    def test_requires_no_configuration(self) -> None:
        service = HelloService()
        assert service.requires_configuration() is False

    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        service = HelloService()
        await service.start()
        assert service.status.state == ServiceState.RUNNING

        await service.stop()
        assert service.status.state == ServiceState.STOPPED

    def test_manager_created(self) -> None:
        service = HelloService()
        assert service.manager is not None

    def test_router_created(self) -> None:
        service = HelloService()
        assert service.router is not None
