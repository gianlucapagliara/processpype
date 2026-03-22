"""Unit tests for service manager."""

import logging

import pytest

from processpype.service.manager import ServiceManager


class ConcreteServiceManager(ServiceManager):
    """Concrete implementation of ServiceManager for testing."""

    async def start(self) -> None:
        """Start the service manager."""

    async def stop(self) -> None:
        """Stop the service manager."""


@pytest.fixture
def logger() -> logging.Logger:
    """Create test logger."""
    return logging.getLogger("test.manager")


@pytest.fixture
def manager(logger: logging.Logger) -> ServiceManager:
    """Create test manager instance."""
    return ConcreteServiceManager(logger)


def test_manager_initialization(
    manager: ServiceManager, logger: logging.Logger
) -> None:
    """Test manager initialization."""
    assert manager.logger == logger


def test_manager_logging(
    manager: ServiceManager, caplog: pytest.LogCaptureFixture
) -> None:
    """Test manager logging functionality."""
    test_message = "Test log message"

    with caplog.at_level(logging.INFO):
        manager.logger.info(test_message)
        assert test_message in caplog.text
