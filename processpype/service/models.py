"""Core models for service state tracking."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class ServiceState(StrEnum):
    """Service lifecycle states."""

    INITIALIZED = "initialized"
    CONFIGURED = "configured"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ServiceStatus(BaseModel):
    """Tracks current state and metadata of a service instance."""

    state: ServiceState
    error: str | None = None
    metadata: dict[str, Any] = {}
    is_configured: bool = False


class ApplicationStatus(BaseModel):
    """Overall application status."""

    version: str
    state: ServiceState
    services: dict[str, ServiceStatus]
