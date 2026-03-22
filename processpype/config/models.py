"""Configuration models for ProcessPype.

Defines the unified configuration tree loaded from a single YAML file.
The Pydantic model hierarchy mirrors the YAML structure exactly.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConfigurationModel(BaseModel):
    """Base configuration model with extra fields allowed."""

    model_config = ConfigDict(extra="allow", frozen=True)


class ServiceConfiguration(ConfigurationModel):
    """Base service configuration model."""

    enabled: bool = Field(default=True, description="Whether the service is enabled")
    autostart: bool = Field(
        default=False, description="Whether to start the service automatically"
    )


# --- App ---


class AppConfig(ConfigurationModel):
    """Application identity and environment settings."""

    title: str = Field(default="ProcessPype", description="Application title")
    version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")
    timezone: str = Field(default="UTC", description="Application timezone")


# --- Server ---


class ServerConfig(ConfigurationModel):
    """FastAPI / uvicorn server settings."""

    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    api_prefix: str = Field(default="", description="API route prefix")
    closing_timeout_seconds: int = Field(
        default=60, description="Graceful shutdown timeout in seconds"
    )

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, v: str) -> str:
        if v and not v.startswith("/"):
            v = f"/{v}"
        return v


# --- Observability ---


class RedactionConfig(ConfigurationModel):
    """Secret redaction settings for log output."""

    enabled: bool = Field(default=True, description="Enable secret redaction in logs")
    patterns: list[str] = Field(
        default_factory=lambda: [
            r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*\S+",
        ],
        description="Regex patterns for secret masking",
    )


class ContextConfig(ConfigurationModel):
    """Async-safe context variable injection into log records."""

    enabled: bool = Field(default=True, description="Enable context injection")


class LoggingConfig(ConfigurationModel):
    """Logging subsystem configuration."""

    enabled: bool = Field(
        default=True, description="When False, no logging handlers are installed"
    )
    level: str = Field(default="INFO", description="Root log level")
    format: str = Field(
        default="color", description="Default format: text | color | json"
    )
    loggers: dict[str, str] = Field(
        default_factory=dict,
        description="Per-logger level overrides, e.g. {'noisy.lib': 'WARNING'}",
    )
    custom_levels: dict[str, int] = Field(
        default_factory=dict, description="Custom log level name → numeric value"
    )
    handlers: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Additional dictConfig-style handler defs"
    )
    redaction: RedactionConfig = Field(default_factory=RedactionConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)


class LogfireConfig(ConfigurationModel):
    """Logfire backend specific settings."""

    token: str = Field(default="", description="Logfire API token")
    environment: str = Field(default="", description="Logfire environment tag")


class TracingConfig(ConfigurationModel):
    """Tracing subsystem configuration."""

    enabled: bool = Field(default=False, description="Enable distributed tracing")
    backend: str = Field(
        default="console",
        description="Tracing backend: logfire | otlp_grpc | otlp_http | console",
    )
    service_name: str = Field(default="", description="OTEL service name")
    endpoint: str = Field(default="", description="OTLP collector endpoint")
    logfire: LogfireConfig = Field(default_factory=LogfireConfig)
    sampling_rate: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Trace sampling rate"
    )
    instrumentation_name: str = Field(
        default="processpype",
        description="OpenTelemetry instrumentation scope name",
    )
    instrumentation_version: str = Field(
        default="1.0.0",
        description="OpenTelemetry instrumentation scope version",
    )


class ObservabilityConfig(ConfigurationModel):
    """Combined logging + tracing configuration."""

    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)


# --- Root ---


class ProcessPypeConfig(ConfigurationModel):
    """Root configuration — the entire YAML tree.

    Example YAML::

        app:
          title: "My App"
          environment: production
        server:
          port: 8080
        observability:
          logging:
            level: INFO
            format: json
          tracing:
            enabled: true
            backend: logfire
        services:
          my_service:
            enabled: true
            autostart: true
    """

    app: AppConfig = Field(default_factory=AppConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    services: dict[str, ServiceConfiguration] = Field(
        default_factory=dict, description="Per-service configurations"
    )
