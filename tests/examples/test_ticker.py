"""Tests for the TickerService example."""

import asyncio

import pytest

from processpype.examples.ticker import TickerConfiguration, TickerService
from processpype.service.models import ServiceState


class TestTickerConfiguration:
    def test_defaults(self) -> None:
        config = TickerConfiguration()
        assert config.interval_seconds == 1.0

    def test_custom_interval(self) -> None:
        config = TickerConfiguration(interval_seconds=0.5)
        assert config.interval_seconds == 0.5

    def test_interval_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            TickerConfiguration(interval_seconds=0)

        with pytest.raises(ValueError):
            TickerConfiguration(interval_seconds=-1)


class TestTickerService:
    def test_create(self) -> None:
        service = TickerService()
        assert service.name == "ticker"

    def test_requires_no_configuration(self) -> None:
        service = TickerService()
        assert service.requires_configuration() is False

    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        service = TickerService()
        service.configure({"interval_seconds": 0.05})
        await service.start()
        assert service.status.state == ServiceState.RUNNING

        # Let it tick a few times
        await asyncio.sleep(0.15)

        await service.stop()
        assert service.status.state == ServiceState.STOPPED
        assert service.manager.tick_count >= 2

    @pytest.mark.asyncio
    async def test_stop_without_start(self) -> None:
        service = TickerService()
        # Should not raise
        await service.stop()
        assert service.status.state == ServiceState.STOPPED
