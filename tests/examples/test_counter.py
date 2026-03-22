"""Tests for the CounterService example."""

import pytest

from processpype.examples.counter import (
    CounterConfiguration,
    CounterManager,
    CounterService,
)
from processpype.service.models import ServiceState


class TestCounterConfiguration:
    def test_defaults(self) -> None:
        config = CounterConfiguration()
        assert config.initial_value == 0
        assert config.step == 1

    def test_custom_values(self) -> None:
        config = CounterConfiguration(initial_value=10, step=5)
        assert config.initial_value == 10
        assert config.step == 5

    def test_step_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="step must be positive"):
            CounterConfiguration(step=0)

        with pytest.raises(ValueError, match="step must be positive"):
            CounterConfiguration(step=-1)


class TestCounterManager:
    def test_increment(self) -> None:
        import logging

        manager = CounterManager(logging.getLogger("test"))
        assert manager.value == 0
        assert manager.increment() == 1
        assert manager.increment() == 2
        assert manager.value == 2

    def test_reset(self) -> None:
        import logging

        manager = CounterManager(logging.getLogger("test"))
        manager.increment()
        manager.increment()
        assert manager.reset() == 0
        assert manager.value == 0

    def test_configure_step(self) -> None:
        import logging

        manager = CounterManager(logging.getLogger("test"))
        manager.configure(CounterConfiguration(initial_value=10, step=5))
        assert manager.value == 10
        assert manager.increment() == 15


class TestCounterService:
    def test_create(self) -> None:
        service = CounterService()
        assert service.name == "counter"

    def test_requires_no_configuration(self) -> None:
        service = CounterService()
        assert service.requires_configuration() is False

    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        service = CounterService()
        await service.start()
        assert service.status.state == ServiceState.RUNNING

        await service.stop()
        assert service.status.state == ServiceState.STOPPED

    def test_configure(self) -> None:
        service = CounterService()
        service.configure({"initial_value": 42, "step": 3})
        assert service.config is not None
        assert isinstance(service.config, CounterConfiguration)
        assert service.manager.value == 42

    def test_custom_router_has_counter_routes(self) -> None:
        service = CounterService()
        routes = [r.path for r in service.router.routes]
        prefix = f"/services/{service.name}"
        assert f"{prefix}/value" in routes
        assert f"{prefix}/increment" in routes
        assert f"{prefix}/reset" in routes
