"""Tests for the notification configuration model."""

import pytest
from pydantic import ValidationError

from processpype.services.notification import (
    NotificationChannel,
    NotificationConfiguration,
    NotificationLevel,
)


def test_notification_configuration_defaults():
    """Test the default values of the notification configuration."""
    config = NotificationConfiguration()

    # Check default values
    assert config.enabled_channels == [NotificationChannel.CONSOLE]
    assert config.default_level == NotificationLevel.INFO
    assert config.telegram_token is None
    assert config.telegram_chat_ids == []
    assert config.telegram_session_name == "processpype_notification_bot"
    assert config.telegram_listen_for_messages is False
    assert config.email_smtp_server is None
    assert config.email_smtp_port == 587
    assert config.email_username is None
    assert config.email_password is None
    assert config.email_recipients == []
    assert config.email_sender is None


def test_notification_configuration_custom_values():
    """Test setting custom values for the notification configuration."""
    config = NotificationConfiguration(
        enabled_channels=[
            NotificationChannel.CONSOLE,
            NotificationChannel.EMAIL,
        ],
        default_level=NotificationLevel.WARNING,
        email_smtp_server="smtp.example.com",
        email_smtp_port=465,
        email_username="user@example.com",
        email_password="password",
        email_recipients=["recipient@example.com"],
        email_sender="sender@example.com",
    )

    # Check custom values
    assert config.enabled_channels == [
        NotificationChannel.CONSOLE,
        NotificationChannel.EMAIL,
    ]
    assert config.default_level == NotificationLevel.WARNING
    assert config.email_smtp_server == "smtp.example.com"
    assert config.email_smtp_port == 465
    assert config.email_username == "user@example.com"
    assert config.email_password == "password"
    assert config.email_recipients == ["recipient@example.com"]
    assert config.email_sender == "sender@example.com"

    # Check that Telegram values are still default
    assert config.telegram_token is None
    assert config.telegram_chat_ids == []
    assert config.telegram_session_name == "processpype_notification_bot"
    assert config.telegram_listen_for_messages is False


def test_notification_configuration_validation():
    """Test validation of the notification configuration."""
    # Test with invalid channel
    with pytest.raises(ValidationError):
        NotificationConfiguration(
            enabled_channels=["invalid_channel"],  # type: ignore
        )

    # Test with invalid level
    with pytest.raises(ValidationError):
        NotificationConfiguration(
            default_level="invalid_level",  # type: ignore
        )


def test_notification_configuration_dict_conversion():
    """Test converting the notification configuration to and from a dictionary."""
    config = NotificationConfiguration(
        enabled_channels=[
            NotificationChannel.CONSOLE,
            NotificationChannel.EMAIL,
        ],
        default_level=NotificationLevel.WARNING,
        email_smtp_server="smtp.example.com",
        email_smtp_port=465,
        email_username="user@example.com",
        email_password="password",
        email_recipients=["recipient@example.com"],
        email_sender="sender@example.com",
    )

    # Convert to dict
    config_dict = config.model_dump()

    # Check dict values
    assert "enabled_channels" in config_dict
    assert "default_level" in config_dict
    assert "email_smtp_server" in config_dict
    assert config_dict["enabled_channels"] == ["console", "email"]
    assert config_dict["default_level"] == "warning"
    assert config_dict["email_smtp_server"] == "smtp.example.com"

    # Convert back to object
    config2 = NotificationConfiguration(**config_dict)

    # Check that the values match
    assert config2.enabled_channels == config.enabled_channels
    assert config2.default_level == config.default_level
    assert config2.email_smtp_server == config.email_smtp_server
    assert config2.email_smtp_port == config.email_smtp_port
    assert config2.email_username == config.email_username
    assert config2.email_password == config.email_password
    assert config2.email_recipients == config.email_recipients
    assert config2.email_sender == config.email_sender
