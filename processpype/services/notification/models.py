"""Models for the NotificationService."""

from enum import Enum
from typing import Any

from pydantic import Field

from processpype.core.configuration.models import ServiceConfiguration


class NotificationLevel(str, Enum):
    """Notification severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    """Supported notification channels."""

    CONSOLE = "console"
    TELEGRAM = "telegram"
    EMAIL = "email"


class NotificationConfiguration(ServiceConfiguration):
    """Configuration for the NotificationService."""

    enabled_channels: list[NotificationChannel] = Field(
        default=[NotificationChannel.CONSOLE],
        description="Enabled notification channels",
    )
    default_level: NotificationLevel = Field(
        default=NotificationLevel.INFO,
        description="Default notification level",
    )

    # Telegram-specific configuration
    telegram_token: str | None = Field(
        default=None,
        description="Telegram token. Can be in format 'bot_token' or 'api_id:api_hash:bot_token'",
    )
    telegram_chat_ids: list[str] = Field(
        default=[],
        description="Telegram chat IDs to send notifications to",
    )
    telegram_session_name: str | None = Field(
        default="processpype_notification_bot",
        description="Session name for the Telegram client",
    )
    telegram_listen_for_messages: bool = Field(
        default=False,
        description="Whether to listen for incoming messages from Telegram",
    )

    # Email-specific configuration
    email_smtp_server: str | None = Field(
        default=None,
        description="SMTP server for email notifications",
    )
    email_smtp_port: int = Field(
        default=587,
        description="SMTP port for email notifications",
    )
    email_username: str | None = Field(
        default=None,
        description="SMTP username for email notifications",
    )
    email_password: str | None = Field(
        default=None,
        description="SMTP password for email notifications",
    )
    email_recipients: list[str] = Field(
        default=[],
        description="Email recipients for notifications",
    )
    email_sender: str | None = Field(
        default=None,
        description="Email sender address",
    )


class Notification:
    """Represents a notification message."""

    def __init__(
        self,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        metadata: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ):
        """Initialize a notification.

        Args:
            message: Notification message
            level: Notification level
            metadata: Additional metadata
            timestamp: Notification timestamp (ISO format)
        """
        self.message = message
        self.level = level
        self.metadata = metadata or {}
        self.timestamp = timestamp

    def __repr__(self) -> str:
        """Return string representation of the notification."""
        return f"Notification(level={self.level}, message={self.message})"


class NotificationTemplate:
    """Template for notifications."""

    def __init__(
        self,
        name: str,
        template: str,
        default_level: NotificationLevel = NotificationLevel.INFO,
    ):
        """Initialize a notification template.

        Args:
            name: Template name
            template: Template string (supports Python string formatting)
            default_level: Default notification level for this template
        """
        self.name = name
        self.template = template
        self.default_level = default_level

    def render(self, context: dict[str, Any]) -> str:
        """Render the template with the given context.

        Args:
            context: Template context variables

        Returns:
            Rendered notification message
        """
        return self.template.format(**context)

    def __repr__(self) -> str:
        """Return string representation of the template."""
        return f"NotificationTemplate(name={self.name})"
