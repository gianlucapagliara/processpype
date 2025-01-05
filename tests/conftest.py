"""Test configuration and fixtures."""

import asyncio
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from processpype.core.configuration.models import (
    ApplicationConfiguration,
    ServiceConfiguration,
)


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_config_file() -> Generator[Path, None, None]:
    """Create a temporary configuration file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as f:
        f.write("""
title: Test App
version: 1.0.0
host: localhost
port: 8080
debug: true
environment: testing
services:
  test_service:
    enabled: true
    autostart: true
    metadata:
      key: value
""")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def default_config() -> ApplicationConfiguration:
    """Create a default application configuration."""
    return ApplicationConfiguration(
        title="Test App",
        version="1.0.0",
        host="localhost",
        port=8080,
        debug=True,
        environment="testing",
    )


@pytest.fixture
def service_config() -> ServiceConfiguration:
    """Create a test service configuration."""
    return ServiceConfiguration(enabled=True, autostart=True, metadata={"key": "value"})
