"""Tests for the notification service."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from processpype.services.notification import (
    NotificationChannel,
    NotificationConfiguration,
    NotificationLevel,
    NotificationService,
    NotificationTemplate,
)
from processpype.services.notification.service import NotificationServiceManager


@pytest.fixture
def notification_config():
    """Create a notification configuration for testing."""
    return NotificationConfiguration(
        enabled_channels=[NotificationChannel.CONSOLE, NotificationChannel.EMAIL],
        default_level=NotificationLevel.INFO,
        telegram_token=None,
        telegram_chat_ids=[],
        email_smtp_server="smtp.example.com",
        email_smtp_port=587,
        email_sender="test@example.com",
        email_recipients=["recipient@example.com"],
    )


@pytest.fixture
def notification_service(notification_config):
    """Create a notification service for testing."""
    service = NotificationService()
    service.configure(notification_config)
    return service


@pytest.mark.asyncio
async def test_create_manager(notification_config):
    """Test creating a notification service manager."""
    service = NotificationService()
    service.configure(notification_config)

    # Test the create_manager method
    manager = service.create_manager()
    assert manager is not None
    assert hasattr(manager, "_config")
    assert hasattr(manager, "logger")


@pytest.mark.asyncio
async def test_manager_property(notification_config):
    """Test the manager property."""
    service = NotificationService()
    service.configure(notification_config)

    # Test the manager property
    manager = service.manager
    assert manager is not None
    assert hasattr(manager, "_config")
    assert hasattr(manager, "logger")


@pytest.mark.asyncio
async def test_notify(notification_config):
    """Test the notify method."""
    service = NotificationService()
    service.configure(notification_config)

    # Mock the manager's notify method
    service.manager.notify = AsyncMock()

    # Call the service's notify method
    await service.notify(
        "Test message",
        NotificationLevel.WARNING,
        [NotificationChannel.CONSOLE],
        {"key": "value"},
    )

    # Verify the manager's notify method was called with the correct arguments
    service.manager.notify.assert_awaited_once_with(
        "Test message",
        NotificationLevel.WARNING,
        [NotificationChannel.CONSOLE],
        {"key": "value"},
    )


@pytest.mark.asyncio
async def test_notify_with_template(notification_config):
    """Test the notify_with_template method."""
    service = NotificationService()
    service.configure(notification_config)

    # Mock the manager's notify_with_template method
    service.manager.notify_with_template = AsyncMock()

    # Call the service's notify_with_template method
    await service.notify_with_template(
        "test_template",
        {"name": "Test"},
        NotificationLevel.WARNING,
        [NotificationChannel.CONSOLE],
        {"key": "value"},
    )

    # Verify the manager's notify_with_template method was called with the correct arguments
    service.manager.notify_with_template.assert_awaited_once_with(
        "test_template",
        {"name": "Test"},
        NotificationLevel.WARNING,
        [NotificationChannel.CONSOLE],
        {"key": "value"},
    )


def test_register_template(notification_config):
    """Test the register_template method."""
    service = NotificationService()
    service.configure(notification_config)

    # Mock the manager's register_template method
    service.manager.register_template = MagicMock()

    # Create a template
    template = NotificationTemplate(
        name="test_template",
        template="Hello, {name}!",
    )

    # Call the service's register_template method
    service.register_template(template)

    # Verify the manager's register_template method was called with the correct arguments
    service.manager.register_template.assert_called_once_with(template)


def test_add_telegram_message_handler(notification_config):
    """Test the add_telegram_message_handler method."""
    # Create a configuration with Telegram enabled
    telegram_config = NotificationConfiguration(
        enabled_channels=[NotificationChannel.TELEGRAM],
        default_level=NotificationLevel.INFO,
        telegram_token="test_token",
        telegram_chat_ids=["123456789"],
    )

    service = NotificationService()
    service.configure(telegram_config)

    # Mock the manager's add_telegram_message_handler method
    service.manager.add_telegram_message_handler = MagicMock()

    # Create a handler function
    def handler(event):
        pass

    # Call the service's add_telegram_message_handler method
    service.add_telegram_message_handler(handler)

    # Verify the manager's add_telegram_message_handler method was called with the correct arguments
    service.manager.add_telegram_message_handler.assert_called_once_with(handler)


@pytest.mark.asyncio
async def test_unknown_notification_channel():
    """Test handling of unknown notification channel types."""
    logger = logging.getLogger("test_notification_service")

    # Mock the warning method
    with patch.object(logger, "warning") as mock_warning:
        # Create a service manager directly with a mock config
        # We'll mock the for loop in the start method to simulate an unknown channel
        config = NotificationConfiguration(
            enabled_channels=[NotificationChannel.CONSOLE],
            default_level=NotificationLevel.INFO,
        )
        manager = NotificationServiceManager(config, logger)

        # Mock the _config.enabled_channels property to return a list with an unknown channel
        # This avoids modifying the frozen Pydantic model
        with patch.object(manager, "_config") as mock_config:
            mock_config.enabled_channels = ["CUSTOM"]
            await manager.start()

        # Verify warning was logged for unknown channel
        mock_warning.assert_called_with("Unknown notification channel type: CUSTOM")


@pytest.mark.asyncio
async def test_channel_not_available_for_notification():
    """Test handling when a channel is not available for notification."""
    logger = logging.getLogger("test_notification_service")
    config = NotificationConfiguration(
        enabled_channels=[NotificationChannel.CONSOLE],
        default_level=NotificationLevel.INFO,
    )

    # Create the manager directly
    manager = NotificationServiceManager(config, logger)

    # Start the manager to initialize channels
    await manager.start()

    # Try to send to a channel that doesn't exist
    with patch.object(logger, "warning") as mock_warning:
        await manager.notify("Test message", channels=[NotificationChannel.EMAIL])

        # Verify warning was logged
        mock_warning.assert_called_with(
            f"Channel {NotificationChannel.EMAIL} not available, skipping notification"
        )


@pytest.mark.asyncio
async def test_error_sending_notification():
    """Test handling of errors when sending notifications."""
    logger = logging.getLogger("test_notification_service")
    config = NotificationConfiguration(
        enabled_channels=[NotificationChannel.CONSOLE],
        default_level=NotificationLevel.INFO,
    )

    # Create the manager directly
    manager = NotificationServiceManager(config, logger)

    # Start the manager to initialize channels
    await manager.start()

    # Mock the console channel to raise an exception when sending
    console_channel = manager._channels[NotificationChannel.CONSOLE]
    console_channel.send = AsyncMock(side_effect=Exception("Test error"))

    # Try to send a notification
    with patch.object(logger, "error") as mock_error:
        await manager.notify("Test message")

        # Verify error was logged
        mock_error.assert_called_with(
            f"Error sending notification to {NotificationChannel.CONSOLE}: Test error"
        )


@pytest.mark.asyncio
async def test_telegram_channel_not_available():
    """Test handling when Telegram channel is not available for adding a handler."""
    logger = logging.getLogger("test_notification_service")
    config = NotificationConfiguration(
        enabled_channels=[NotificationChannel.CONSOLE],
        default_level=NotificationLevel.INFO,
    )

    # Create the manager directly
    manager = NotificationServiceManager(config, logger)

    # Start the manager to initialize channels (without Telegram)
    await manager.start()

    # Try to add a Telegram message handler
    with patch.object(logger, "warning") as mock_warning:

        def handler(event):
            pass

        manager.add_telegram_message_handler(handler)

        # Verify warning was logged
        mock_warning.assert_called_with(
            "Telegram channel not available, can't add message handler"
        )


@pytest.mark.asyncio
async def test_telegram_channel_no_handler_support():
    """Test handling when Telegram channel doesn't support message handlers."""
    logger = logging.getLogger("test_notification_service")
    config = NotificationConfiguration(
        enabled_channels=[NotificationChannel.TELEGRAM],
        default_level=NotificationLevel.INFO,
        telegram_token="test_token",
        telegram_chat_ids=["123456789"],
    )

    # Create the manager directly
    manager = NotificationServiceManager(config, logger)

    # Create a mock Telegram channel without add_message_handler method
    mock_telegram_channel = AsyncMock()
    # Explicitly remove the add_message_handler attribute
    if hasattr(mock_telegram_channel, "add_message_handler"):
        delattr(mock_telegram_channel, "add_message_handler")

    # Replace the Telegram channel in the manager
    manager._channels[NotificationChannel.TELEGRAM] = mock_telegram_channel

    # Try to add a Telegram message handler
    with patch.object(logger, "warning") as mock_warning:

        def handler(event):
            pass

        # Call the method
        manager.add_telegram_message_handler(handler)

        # Verify warning was logged
        mock_warning.assert_called_with(
            "Telegram channel doesn't support message handlers"
        )
