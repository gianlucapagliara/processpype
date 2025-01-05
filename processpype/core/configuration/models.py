"""Configuration models for ProcessPype."""

from typing import Any

from pydantic import BaseModel, Field


class ConfigurationModel(BaseModel):
    """Base configuration model."""

    class Config:
        """Pydantic configuration."""

        extra = "allow"
        frozen = True


class ServiceConfiguration(ConfigurationModel):
    """Base service configuration model."""

    name: str | None = Field(default=None, description="Service name")
    enabled: bool = Field(default=True, description="Whether the service is enabled")
    autostart: bool = Field(
        default=False, description="Whether to start the service automatically"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Service metadata"
    )


class ApplicationConfiguration(ConfigurationModel):
    """Application configuration model."""

    title: str = Field(default="ProcessPype", description="API title")
    version: str = Field(default="0.1.0", description="API version")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment name")
    logfire_key: str | None = Field(default=None, description="Logfire API key")
    services: dict[str, ServiceConfiguration] = Field(
        default_factory=dict, description="Service configurations"
    )
