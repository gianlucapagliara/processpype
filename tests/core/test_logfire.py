"""Unit tests for logging functionality."""

import logging
from unittest.mock import patch

import pytest
from fastapi import FastAPI

from processpype.core.logfire import (
    ServiceLogContext,
    get_service_logger,
    instrument_fastapi,
    setup_logfire,
)


def test_service_log_context() -> None:
    """Test ServiceLogContext model."""
    context = ServiceLogContext(
        service_name="test_service", service_state="running", metadata={"key": "value"}
    )

    assert context.service_name == "test_service"
    assert context.service_state == "running"
    assert context.metadata == {"key": "value"}


def test_service_log_context_defaults() -> None:
    """Test ServiceLogContext default values."""
    context = ServiceLogContext(service_name="test_service", service_state="running")

    assert context.metadata == {}


@pytest.fixture
def mock_app() -> FastAPI:
    """Create mock FastAPI application."""
    return FastAPI()


def test_setup_logfire(mock_app: FastAPI) -> None:
    """Test Logfire setup configuration."""
    with (
        patch("logfire.configure") as mock_configure,
        patch("logfire.instrument_fastapi") as mock_instrument_fastapi,
    ):
        # Call setup_logfire with the required token parameter
        setup_logfire(token="test_token", environment="testing", app_name="test_app")

        # Instrument FastAPI app separately
        instrument_fastapi(mock_app)

        # Verify Logfire configuration
        mock_configure.assert_called_once_with(
            service_name="test_app", token="test_token", environment="testing"
        )

        # Verify instrumentation setup
        mock_instrument_fastapi.assert_called_once_with(mock_app)


def test_setup_logfire_defaults(mock_app: FastAPI) -> None:
    """Test Logfire setup with default values."""
    with patch("logfire.configure") as mock_configure:
        # Call setup_logfire with the required token parameter
        setup_logfire(token="test_token")

        mock_configure.assert_called_once_with(
            service_name="processpype", token="test_token", environment=None
        )


def test_get_service_logger() -> None:
    """Test service logger creation."""
    logger = get_service_logger("test_service")

    assert isinstance(logger, logging.Logger)
    assert logger.name == "processpype.services.test_service"


def test_get_service_logger_unique() -> None:
    """Test that different service loggers are unique."""
    logger1 = get_service_logger("service1")
    logger2 = get_service_logger("service2")

    assert logger1 != logger2
    assert logger1.name != logger2.name
