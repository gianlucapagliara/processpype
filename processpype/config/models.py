"""Configuration models for ProcessPype.

Defines the unified configuration tree loaded from a single YAML file.
The Pydantic model hierarchy mirrors the YAML structure exactly.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag, field_validator


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


# --- Communications ---


class TelegramChatConfig(ConfigurationModel):
    """Configuration for a single Telegram chat/channel destination."""

    chat_id: str = Field(description="Chat/channel identifier")
    topic_id: int | None = Field(default=None, description="Forum topic ID")
    command_authorized: bool = Field(
        default=False, description="Accept commands from this chat"
    )
    active: bool = Field(default=True, description="Whether this chat is active")

    @field_validator("chat_id")
    @classmethod
    def validate_chat_id_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("chat_id cannot be empty")
        return v


class CommunicatorBackendConfig(ConfigurationModel):
    """Base configuration for a communicator backend instance."""

    type: str = Field(description="Backend type: telegram | email | custom")
    enabled: bool = Field(default=True, description="Whether this backend is active")
    labels: list[str] = Field(
        default_factory=lambda: ["default"],
        description="Labels this backend handles",
    )

    @field_validator("labels")
    @classmethod
    def validate_labels_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("labels cannot be empty — at least one label is required")
        return v


class TelegramCommunicatorConfig(CommunicatorBackendConfig):
    """Telegram-specific communicator settings."""

    api_id: int = Field(description="Telegram API ID")
    api_hash: str = Field(description="Telegram API hash")
    token: str = Field(description="Bot token")
    session_string: str = Field(default="", description="Session string for auth")
    listen_to_commands: bool = Field(
        default=False, description="Enable incoming message handling"
    )
    chats: dict[str, TelegramChatConfig] = Field(
        default_factory=dict,
        description="Chat configurations keyed by label",
    )


class EmailCommunicatorConfig(CommunicatorBackendConfig):
    """Email-specific communicator settings (send-only)."""

    host: str = Field(default="localhost", description="SMTP host")
    port: int = Field(default=587, description="SMTP port")
    username: str = Field(default="", description="SMTP username")
    password: str = Field(default="", description="SMTP password")
    from_address: str = Field(description="Sender email address")
    use_tls: bool = Field(default=True, description="Use TLS")
    start_tls: bool = Field(
        default=False, description="Use STARTTLS after connecting (for port 587)"
    )
    default_recipients: list[str] = Field(
        default_factory=list,
        description="Default recipient addresses",
    )


def _communicator_backend_discriminator(v: Any) -> str:
    if isinstance(v, dict):
        typ = v.get("type")
        if typ is None:
            raise ValueError("Backend config must include a 'type' field")
        return typ if typ in ("telegram", "email") else "base"
    typ = getattr(v, "type", None)
    if typ is None:
        raise ValueError("Backend config must include a 'type' field")
    return typ if typ in ("telegram", "email") else "base"


CommunicatorBackendConfigType = (
    Annotated[TelegramCommunicatorConfig, Tag("telegram")]
    | Annotated[EmailCommunicatorConfig, Tag("email")]
    | Annotated[CommunicatorBackendConfig, Tag("base")]
)


class CommunicationsConfig(ConfigurationModel):
    """Top-level communications configuration."""

    enabled: bool = Field(default=False, description="Enable communication system")
    backends: dict[
        str,
        Annotated[
            CommunicatorBackendConfigType,
            Discriminator(_communicator_backend_discriminator),
        ],
    ] = Field(
        default_factory=dict,
        description="Named communicator backends",
    )


# --- Secrets ---


class AWSBackendConfig(ConfigurationModel):
    """AWS Secrets Manager backend configuration.

    The ``prefix`` is transparently prepended to all secret names.  For
    example, with ``prefix: "production/exchanges"`` a request for key
    ``binance`` actually fetches ``production/exchanges/binance`` from AWS.
    """

    type: Literal["aws"] = "aws"
    region_name: str = Field(default="", description="AWS region name")
    profile_name: str = Field(default="", description="AWS profile name")
    prefix: str = Field(
        default="",
        description="Prefix prepended to all secret names (e.g. 'production/exchanges')",
    )


class FileBackendConfig(ConfigurationModel):
    """YAML file backend configuration."""

    type: Literal["file"] = "file"
    path: str = Field(default="", description="Path to YAML secrets file")
    prefix: str = Field(
        default="",
        description="Prefix prepended to key lookups inside the YAML file",
    )


class DotenvBackendConfig(ConfigurationModel):
    """Dotenv file backend configuration.

    Reads key-value pairs from a ``.env`` file.
    """

    type: Literal["dotenv"] = "dotenv"
    path: str = Field(default=".env", description="Path to the .env file")
    prefix: str = Field(
        default="",
        description="Prefix prepended to key lookups in the .env file",
    )


class EnvBackendConfig(ConfigurationModel):
    """Environment variables backend configuration."""

    type: Literal["env"] = "env"
    prefix: str = Field(
        default="",
        description="Prefix prepended to env var names (e.g. 'APP_')",
    )


def _secrets_backend_discriminator(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("type", "env"))
    return str(getattr(value, "type", "env"))


BackendConfig = Annotated[
    Annotated[AWSBackendConfig, Tag("aws")]
    | Annotated[FileBackendConfig, Tag("file")]
    | Annotated[DotenvBackendConfig, Tag("dotenv")]
    | Annotated[EnvBackendConfig, Tag("env")],
    Discriminator(_secrets_backend_discriminator),
]


class SecretsConfig(ConfigurationModel):
    """Secrets subsystem configuration.

    Example YAML::

        secrets:
          enabled: true
          backends:
            aws:
              type: aws
              region_name: eu-west-1
              prefix: "production/myapp"
            env:
              type: env
            dotenv:
              type: dotenv
              path: .env
            local:
              type: file
              path: ./secrets.yaml
          load:
            - "aws:*"
            - "env:API_KEY"
            - "dotenv:DB_*"
            - "local:*"
          cache_enabled: true
    """

    enabled: bool = Field(default=False, description="Enable the secrets subsystem")
    backends: dict[str, BackendConfig] = Field(
        default_factory=dict, description="Named backend configurations"
    )
    load: list[str] = Field(
        default_factory=list, description="Secret declarations: 'backend_name:pattern'"
    )

    @field_validator("load")
    @classmethod
    def validate_load_declarations(cls, v: list[str]) -> list[str]:
        for decl in v:
            if ":" not in decl:
                raise ValueError(
                    f"Invalid secret declaration '{decl}': must be 'backend_name:pattern'"
                )
        return v

    cache_enabled: bool = Field(
        default=True, description="Cache fetched secrets in memory"
    )


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
        secrets:
          enabled: true
          backends:
            aws:
              type: aws
              region_name: eu-west-1
              prefix: "production/myapp"
            env:
              type: env
          load:
            - "aws:*"
            - "env:API_KEY"
        services:
          my_service:
            enabled: true
            autostart: true
    """

    app: AppConfig = Field(default_factory=AppConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    secrets: SecretsConfig = Field(default_factory=SecretsConfig)
    communications: CommunicationsConfig = Field(default_factory=CommunicationsConfig)
    services: dict[str, ServiceConfiguration] = Field(
        default_factory=dict, description="Per-service configurations"
    )
