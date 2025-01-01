"""Core models for ProcessPype."""

from enum import Enum
from typing import Any

from pydantic import BaseModel


class ServiceState(str, Enum):
    """Service state enumeration."""

    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ServiceStatus(BaseModel):
    """Service status model."""

    state: ServiceState
    error: str | None = None
    metadata: dict[str, Any] = {}


class ApplicationStatus(BaseModel):
    """Application status model."""

    version: str
    state: ServiceState
    services: dict[str, ServiceStatus]
