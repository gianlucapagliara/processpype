"""Common test fixtures."""

import asyncio
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from processpype.config.models import AppConfig, ProcessPypeConfig, ServerConfig


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_app() -> FastAPI:
    """Create a test FastAPI application."""
    return FastAPI(
        title="Test App",
        version="1.0.0",
    )


@pytest.fixture
def test_client(test_app: FastAPI) -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(test_app)


@pytest.fixture
def test_config_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test configuration files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def test_config_file(test_config_dir: Path) -> Path:
    """Create a test configuration file."""
    config_file = test_config_dir / "test_config.yaml"
    with open(config_file, "w") as f:
        f.write(
            """
app:
  title: Test App
  version: 1.0.0
  environment: testing
  debug: true
server:
  host: localhost
  port: 8080
services:
  test_service:
    autostart: true
"""
        )
    return config_file


@pytest.fixture
def app_config() -> ProcessPypeConfig:
    """Create a test application configuration."""
    return ProcessPypeConfig(
        app=AppConfig(
            title="Test App",
            version="1.0.0",
            environment="testing",
            debug=True,
        ),
        server=ServerConfig(
            host="localhost",
            port=8080,
            closing_timeout_seconds=5,
        ),
        services={},
    )
