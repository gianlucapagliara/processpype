"""Logging configuration for ProcessPype.

This module provides logging configuration and integration with Logfire service.
It includes structured logging setup, FastAPI instrumentation, and service-specific logging contexts.
"""

import logging
from typing import Any

import logfire
from fastapi import FastAPI
from pydantic import BaseModel


class ServiceLogContext(BaseModel):
    """Service log context model.

    Provides structured context for service-specific logging entries.

    Attributes:
        service_name: Name of the service generating the log
        service_state: Current state of the service
        metadata: Additional contextual information for logging
    """

    service_name: str
    service_state: str
    metadata: dict[str, Any] = {}


def setup_logfire(
    app: FastAPI,
    app_name: str = "processpype",
    token: str | None = None,
    environment: str | None = None,
    **kwargs: Any,
) -> None:
    """Setup application logging with Logfire integration.

    Configures logging handlers, initializes Logfire integration,
    and sets up FastAPI and Pydantic instrumentation.

    Args:
        app: FastAPI application instance to instrument
        app_name: Application name for logging context (default: "processpype")
        token: Logfire API token for authentication
        environment: Environment name (e.g., "production", "development")
        **kwargs: Additional configuration options for Logfire
    """
    # Configure base logging with Logfire handler
    logging.basicConfig(handlers=[logfire.LogfireLoggingHandler()])

    # Initialize Logfire with application context
    logfire.configure(
        service_name=app_name,
        token=token,
        environment=environment,
    )

    # Setup automatic instrumentation
    logfire.instrument_pydantic()  # Enable Pydantic model logging
    logfire.instrument_fastapi(app)  # Enable FastAPI request/response logging


def get_service_logger(service_name: str) -> logging.Logger:
    """Get a logger for a service with context.

    Creates a logger instance with service-specific naming and context.
    The logger name follows the pattern: processpype.services.<service_name>

    Args:
        service_name: Name of the service requiring logging

    Returns:
        Logger instance configured with service context
    """
    logger = logging.getLogger(f"processpype.services.{service_name}")
    return logger
