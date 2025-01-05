"""Unit tests for core models."""

import pytest

from processpype.core.models import ApplicationStatus, ServiceState, ServiceStatus


def test_service_state_values() -> None:
    """Test ServiceState enum values."""
    assert ServiceState.INITIALIZED.value == "initialized"
    assert ServiceState.STARTING.value == "starting"
    assert ServiceState.RUNNING.value == "running"
    assert ServiceState.STOPPING.value == "stopping"
    assert ServiceState.STOPPED.value == "stopped"
    assert ServiceState.ERROR.value == "error"


def test_service_status_creation() -> None:
    """Test ServiceStatus model creation and defaults."""
    # Test with minimal parameters
    status = ServiceStatus(state=ServiceState.INITIALIZED)
    assert status.state == ServiceState.INITIALIZED
    assert status.error is None
    assert status.metadata == {}

    # Test with all parameters
    status = ServiceStatus(
        state=ServiceState.ERROR, error="Test error", metadata={"key": "value"}
    )
    assert status.state == ServiceState.ERROR
    assert status.error == "Test error"
    assert status.metadata == {"key": "value"}


def test_service_status_validation() -> None:
    """Test ServiceStatus model validation."""
    # Test invalid state
    with pytest.raises(ValueError):
        ServiceStatus(state="invalid", metadata={})  # type: ignore[arg-type]

    # Test invalid metadata type
    with pytest.raises(ValueError):
        ServiceStatus(
            state=ServiceState.RUNNING,
            metadata=123,  # type: ignore[arg-type]
        )


def test_application_status_creation() -> None:
    """Test ApplicationStatus model creation."""
    services = {
        "service1": ServiceStatus(state=ServiceState.RUNNING),
        "service2": ServiceStatus(state=ServiceState.STOPPED),
    }

    status = ApplicationStatus(
        version="1.0.0", state=ServiceState.RUNNING, services=services
    )

    assert status.version == "1.0.0"
    assert status.state == ServiceState.RUNNING
    assert len(status.services) == 2
    assert status.services["service1"].state == ServiceState.RUNNING
    assert status.services["service2"].state == ServiceState.STOPPED


def test_application_status_validation() -> None:
    """Test ApplicationStatus model validation."""
    # Test missing required fields
    with pytest.raises(ValueError):
        ApplicationStatus(version="1.0.0", state=ServiceState.RUNNING)  # type: ignore

    # Test invalid version type
    with pytest.raises(ValueError):
        ApplicationStatus(
            version=1.0,  # type: ignore
            state=ServiceState.RUNNING,
            services={},
        )

    # Test invalid services type
    with pytest.raises(ValueError):
        ApplicationStatus(
            version="1.0.0",
            state=ServiceState.RUNNING,
            services=[],  # type: ignore
        )
