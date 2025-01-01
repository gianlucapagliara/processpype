"""Logging configuration for ProcessPype."""

import logging
from typing import Any

import logfire
from fastapi import FastAPI
from pydantic import BaseModel


class ServiceLogContext(BaseModel):
    """Service log context model."""
    service_name: str
    service_state: str
    metadata: dict[str, Any] = {}

def setup_logfire(
    app: FastAPI,
    app_name: str = "processpype",
    token: str | None = None,
    environment: str | None = None,
    **kwargs: Any
) -> None:
    """Setup application logging with Logfire integration.

    Args:
        app_name: Application name for logging context
        log_level: Logging level
        logfire_key: Optional Logfire API key
    """
    # Base logging configuration
    logging.basicConfig(
        handlers=[logfire.LogfireLoggingHandler()]
    )

    # Initialize Logfire
    logfire.configure(
        service_name=app_name,
        token=token,
        environment=environment,  # Can be configured based on env
    )

    logfire.instrument_pydantic()  # Defaults to record='all'
    logfire.instrument_fastapi(app)


def get_service_logger(service_name: str) -> logging.Logger:
    """Get a logger for a service with context.

    Args:
        service_name: Name of the service

    Returns:
        Logger instance with service context
    """
    logger = logging.getLogger(f"processpype.services.{service_name}")
    return logger
