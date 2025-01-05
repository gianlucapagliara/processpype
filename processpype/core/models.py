"""Core models for ProcessPype.

This module defines the core data models used throughout the ProcessPype framework.
It includes enums and Pydantic models for service state tracking and status management.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel


class ServiceState(str, Enum):
    """Service state enumeration.

    Represents the possible states a service can be in during its lifecycle:
    - INITIALIZED: Service is created but not yet started
    - STARTING: Service is in the process of starting
    - RUNNING: Service is actively running
    - STOPPING: Service is in the process of shutting down
    - STOPPED: Service has been stopped
    - ERROR: Service encountered an error
    """

    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ServiceStatus(BaseModel):
    """Service status model.

    Tracks the current state and metadata of a service instance.

    Attributes:
        state: Current state of the service
        error: Error message if service is in error state
        metadata: Additional service-specific status information
    """

    state: ServiceState
    error: str | None = None
    metadata: dict[str, Any] = {}


class ApplicationStatus(BaseModel):
    """Application status model.

    Represents the overall status of the ProcessPype application.

    Attributes:
        version: Application version string
        state: Current state of the application
        services: Dictionary mapping service names to their status
    """

    version: str
    state: ServiceState
    services: dict[str, ServiceStatus]
