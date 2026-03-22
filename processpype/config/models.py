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

    level: str = Field(default="INFO", description="Root log level")
    format: str = Field(
        default="color", description="Default format: text | color | json"
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


class ObservabilityConfig(ConfigurationModel):
    """Combined logging + tracing configuration."""

    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)


# --- Notifications ---


class EmailConfig(ConfigurationModel):
    """Email notification channel settings."""

    enabled: bool = Field(default=False, description="Enable email notifications")
    smtp_host: str = Field(default="", description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: str = Field(default="", description="SMTP username")
    smtp_password: str = Field(default="", description="SMTP password")
    from_address: str = Field(default="", description="Sender email address")
    default_recipients: list[str] = Field(
        default_factory=list, description="Default recipient addresses"
    )


class TelegramChatConfig(ConfigurationModel):
    """Configuration for a single Telegram chat destination."""

    label: str = Field(default="default", description="Chat label identifier")
    chat_id: int = Field(description="Telegram chat ID")
    topic_id: int | None = Field(default=None, description="Optional topic/thread ID")


class TelegramConfig(ConfigurationModel):
    """Telegram notification channel settings."""

    enabled: bool = Field(default=False, description="Enable Telegram notifications")
    api_id: int = Field(default=0, description="Telegram API ID")
    api_hash: str = Field(default="", description="Telegram API hash")
    session_name: str = Field(default="processpype", description="Session file name")
    chats: list[TelegramChatConfig] = Field(
        default_factory=list, description="Chat destinations"
    )


class NotificationsConfig(ConfigurationModel):
    """Notification subsystem configuration."""

    enabled: bool = Field(default=False, description="Enable notifications")
    email: EmailConfig = Field(default_factory=EmailConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)


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
        notifications:
          enabled: false
        services:
          my_service:
            enabled: true
            autostart: true
    """

    app: AppConfig = Field(default_factory=AppConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    services: dict[str, ServiceConfiguration] = Field(
        default_factory=dict, description="Per-service configurations"
    )
