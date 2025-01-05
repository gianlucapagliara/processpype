"""Unit tests for service manager."""

import logging

import pytest

from processpype.core.service.manager import ServiceManager


@pytest.fixture
def logger() -> logging.Logger:
    """Create test logger."""
    return logging.getLogger("test.manager")


@pytest.fixture
def manager(logger: logging.Logger) -> ServiceManager:
    """Create test manager instance."""
    return ServiceManager(logger)


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
