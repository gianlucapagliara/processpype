"""Tests for the Cronitor configuration."""

import pytest
from pydantic import ValidationError

from processpype.services.monitoring.cronitor.config import CronitorConfiguration


def test_default_config() -> None:
    """Test the default Cronitor configuration."""
    config = CronitorConfiguration()

    assert config.enabled is True
    assert config.api_key == ""
    assert config.monitor_key == ""
    assert config.interval == 60.0
    assert config.state == "run"
    assert config.environment == ""
    assert config.series == ""
    assert config.metrics == {}


def test_custom_config() -> None:
    """Test a custom Cronitor configuration."""
    config = CronitorConfiguration(
        enabled=False,
        api_key="test_api_key",
        monitor_key="test_monitor_key",
        interval=30.0,
        state="complete",
        environment="test",
        series="test_series",
        metrics={"test_metric": 10.0},
    )

    assert config.enabled is False
    assert config.api_key == "test_api_key"
    assert config.monitor_key == "test_monitor_key"
    assert config.interval == 30.0
    assert config.state == "complete"
    assert config.environment == "test"
    assert config.series == "test_series"
    assert config.metrics == {"test_metric": 10.0}


def test_invalid_interval() -> None:
    """Test validation of invalid interval values."""
    # Test interval less than 1.0
    with pytest.raises(ValidationError) as excinfo:
        CronitorConfiguration(interval=0.5)

    assert "Input should be greater than or equal to 1" in str(excinfo.value)


def test_invalid_state() -> None:
    """Test validation of invalid state values."""
    # Test invalid state
    with pytest.raises(ValidationError) as excinfo:
        CronitorConfiguration(state="invalid")

    assert "State must be one of: run, complete, fail" in str(excinfo.value)


def test_from_dict() -> None:
    """Test creating a configuration from a dictionary."""
    config_dict = {
        "enabled": False,
        "api_key": "test_api_key",
        "monitor_key": "test_monitor_key",
        "interval": 30.0,
        "state": "fail",
        "environment": "test",
        "series": "test_series",
        "metrics": {"test_metric": 10.0},
    }

    config = CronitorConfiguration.model_validate(config_dict)

    assert config.enabled is False
    assert config.api_key == "test_api_key"
    assert config.monitor_key == "test_monitor_key"
    assert config.interval == 30.0
    assert config.state == "fail"
    assert config.environment == "test"
    assert config.series == "test_series"
    assert config.metrics == {"test_metric": 10.0}


def test_to_dict() -> None:
    """Test converting a configuration to a dictionary."""
    config = CronitorConfiguration(
        enabled=False,
        api_key="test_api_key",
        monitor_key="test_monitor_key",
        interval=30.0,
        state="complete",
        environment="test",
        series="test_series",
        metrics={"test_metric": 10.0},
    )

    config_dict = config.model_dump()

    # Check that the dictionary contains the expected values
    assert config_dict["api_key"] == "test_api_key"
    assert config_dict["monitor_key"] == "test_monitor_key"
    assert config_dict["interval"] == 30.0
    assert config_dict["state"] == "complete"
    assert config_dict["environment"] == "test"
    assert config_dict["series"] == "test_series"
    assert config_dict["metrics"] == {"test_metric": 10.0}

    # Check that the enabled field is accessible through the config object
    assert config_dict["enabled"] is False
