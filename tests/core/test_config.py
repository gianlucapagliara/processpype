"""Tests for configuration system."""

import os

import pytest

from processpype.core.config import ConfigurationManager
from processpype.core.config.models import (
    ApplicationConfiguration,
    ServiceConfiguration,
)
from processpype.core.config.providers import EnvProvider, FileProvider


@pytest.mark.asyncio
async def test_config_manager_basic():
    """Test ConfigurationManager basic operations."""
    manager1 = ConfigurationManager()
    manager2 = ConfigurationManager()
    assert manager1 is not manager2  # No longer a singleton


@pytest.mark.asyncio
async def test_load_application_config_from_kwargs():
    """Test loading configuration from kwargs."""
    config = await ConfigurationManager.load_application_config(
        title="Test App", port=9000
    )
    assert isinstance(config, ApplicationConfiguration)
    assert config.title == "Test App"
    assert config.port == 9000


@pytest.mark.asyncio
async def test_load_application_config_from_file(temp_config_file):
    """Test loading configuration from file."""
    config = await ConfigurationManager.load_application_config(
        config_file=temp_config_file
    )
    assert isinstance(config, ApplicationConfiguration)
    assert config.title == "Test App"
    assert config.port == 8080
    assert config.services["test_service"].enabled is True


@pytest.mark.asyncio
async def test_env_provider():
    """Test environment variable provider."""
    os.environ["PROCESSPYPE_TITLE"] = "Env App"
    os.environ["PROCESSPYPE_PORT"] = "9000"
    os.environ["PROCESSPYPE_SERVICES__TEST__ENABLED"] = "true"

    provider = EnvProvider()
    config = await provider.load()

    assert config["title"] == "Env App"
    assert config["port"] == "9000"
    assert config["services"]["test"]["enabled"] == "true"


@pytest.mark.asyncio
async def test_file_provider(temp_config_file):
    """Test file provider."""
    provider = FileProvider(temp_config_file)
    config = await provider.load()

    assert config["title"] == "Test App"
    assert config["port"] == 8080
    assert config["services"]["test_service"]["enabled"] is True


@pytest.mark.asyncio
async def test_provider_precedence():
    """Test provider loading precedence."""
    os.environ["PROCESSPYPE_TITLE"] = "Env App"

    manager = ConfigurationManager()
    await manager.add_provider(FileProvider("nonexistent.yaml"))  # Should be ignored
    await manager.add_provider(EnvProvider())

    await manager.initialize()

    assert manager.get("title") == "Env App"


@pytest.mark.asyncio
async def test_configuration_models():
    """Test configuration model validation."""
    # Test ApplicationConfiguration
    config = ApplicationConfiguration(
        title="Test",
        port=-1,  # Invalid port
    )
    assert config.title == "Test"
    assert config.port == -1  # TODO: Add validation

    # Test ServiceConfiguration
    service_config = ServiceConfiguration(enabled=True, metadata={"test": "value"})
    assert service_config.enabled is True
    assert service_config.metadata["test"] == "value"


@pytest.mark.asyncio
async def test_config_manager_operations():
    """Test ConfigurationManager operations."""
    manager = ConfigurationManager()

    # Test set and get
    await manager.set("test_key", "test_value")
    assert manager.get("test_key") == "test_value"

    # Test get with default
    assert manager.get("nonexistent", "default") == "default"

    # Test model conversion
    await manager.set("title", "Test App")
    await manager.set("port", 8080)

    config = manager.get_model(ApplicationConfiguration)
    assert isinstance(config, ApplicationConfiguration)
    assert config.title == "Test App"
    assert config.port == 8080
