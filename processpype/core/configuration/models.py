"""Configuration models for ProcessPype."""

from pydantic import BaseModel, Field, field_validator


class ConfigurationModel(BaseModel):
    """Base configuration model."""

    class Config:
        """Pydantic configuration."""

        extra = "allow"
        frozen = True


class ServiceConfiguration(ConfigurationModel):
    """Base service configuration model."""

    enabled: bool = Field(
        default=True,
        description="Whether the service is enabled",
    )
    autostart: bool = Field(
        default=False,
        description="Whether to start the service automatically",
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
    api_prefix: str = Field(default="", description="API prefix")
    closing_timeout_seconds: int = Field(
        default=60, description="Closing timeout in seconds"
    )

    @field_validator("api_prefix")
    def validate_api_prefix(cls, v: str) -> str:
        """Validate the API prefix."""
        if v and not v.startswith("/"):
            v = f"/{v}"
        return v
