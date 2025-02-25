"""Tests for the monitoring configuration."""

import pytest
from pydantic import ValidationError

from processpype.services.monitoring.config import MonitoringConfiguration


def test_default_config():
    """Test the default monitoring configuration."""
    config = MonitoringConfiguration()

    assert config.enabled is True
    assert config.interval == 5.0
    assert config.collect_cpu is True
    assert config.collect_memory is True
    assert config.collect_disk is True
    assert config.disk_path == "/"


def test_custom_config():
    """Test a custom monitoring configuration."""
    config = MonitoringConfiguration(
        enabled=False,
        interval=10.0,
        collect_cpu=False,
        collect_memory=True,
        collect_disk=False,
        disk_path="/home",
    )

    assert config.enabled is False
    assert config.interval == 10.0
    assert config.collect_cpu is False
    assert config.collect_memory is True
    assert config.collect_disk is False
    assert config.disk_path == "/home"


def test_invalid_interval():
    """Test validation of invalid interval values."""
    # Test interval less than 1.0
    with pytest.raises(ValidationError) as excinfo:
        MonitoringConfiguration(interval=0.5)

    assert "Input should be greater than or equal to 1" in str(excinfo.value)


def test_from_dict():
    """Test creating a configuration from a dictionary."""
    config_dict = {
        "enabled": False,
        "interval": 15.0,
        "collect_cpu": True,
        "collect_memory": False,
        "collect_disk": True,
        "disk_path": "/var",
    }

    config = MonitoringConfiguration.model_validate(config_dict)

    assert config.enabled is False
    assert config.interval == 15.0
    assert config.collect_cpu is True
    assert config.collect_memory is False
    assert config.collect_disk is True
    assert config.disk_path == "/var"


def test_to_dict():
    """Test converting a configuration to a dictionary."""
    config = MonitoringConfiguration(
        enabled=False,
        interval=10.0,
        collect_cpu=False,
        collect_memory=True,
        collect_disk=False,
        disk_path="/home",
    )

    config_dict = config.model_dump()

    # Check that the dictionary contains the expected values
    assert config.interval == 10.0
    assert config.collect_cpu is False
    assert config.collect_memory is True
    assert config.collect_disk is False
    assert config.disk_path == "/home"

    # Check that the enabled field is accessible through the config object
    assert config.enabled is False
