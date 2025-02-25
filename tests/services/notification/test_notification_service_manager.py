"""Tests for the notification service manager."""

import logging
from unittest.mock import AsyncMock, patch

import pytest

from processpype.services.notification import (
    NotificationChannel,
    NotificationConfiguration,
    NotificationLevel,
    NotificationTemplate,
)
from processpype.services.notification.service import NotificationServiceManager


@pytest.fixture
def notification_config():
    """Create a notification service configuration for testing."""
    return NotificationConfiguration(
        enabled_channels=[NotificationChannel.CONSOLE],
        default_level=NotificationLevel.INFO,
    )


@pytest.fixture
def notification_manager(notification_config):
    """Create a notification service manager for testing."""
    logger = logging.getLogger("test_notification_manager")
    return NotificationServiceManager(notification_config, logger)


@pytest.mark.asyncio
async def test_notification_manager_start(notification_manager):
    """Test starting the notification service manager."""
    # Mock the ConsoleNotificationChannel.initialize method
    with patch(
        "processpype.services.notification.channels.console.ConsoleNotificationChannel.initialize",
        new_callable=AsyncMock,
    ) as mock_initialize:
        # Start the manager
        await notification_manager.start()

        # Check that the console channel was initialized
        mock_initialize.assert_called_once()

        # Check that the channel was added to the manager
        assert NotificationChannel.CONSOLE in notification_manager._channels

        # Stop the manager
        await notification_manager.stop()


@pytest.mark.asyncio
async def test_notification_manager_start_multiple_channels():
    """Test starting the notification service manager with multiple channels."""
    # Configure multiple channels
    config = NotificationConfiguration(
        enabled_channels=[
            NotificationChannel.CONSOLE,
            NotificationChannel.EMAIL,
        ],
        email_smtp_server="smtp.example.com",
        email_smtp_port=587,
        email_username="user@example.com",
        email_password="password",
        email_recipients=["recipient@example.com"],
        email_sender="sender@example.com",
    )

    # Create the manager
    logger = logging.getLogger("test_notification_manager")
    manager = NotificationServiceManager(config, logger)

    # Mock the channel initialize methods
    with (
        patch(
            "processpype.services.notification.channels.console.ConsoleNotificationChannel.initialize",
            new_callable=AsyncMock,
        ) as mock_console_initialize,
        patch(
            "processpype.services.notification.channels.email.EmailNotificationChannel.initialize",
            new_callable=AsyncMock,
        ) as mock_email_initialize,
    ):
        # Start the manager
        await manager.start()

        # Check that both channels were initialized
        mock_console_initialize.assert_called_once()
        mock_email_initialize.assert_called_once()

        # Check that both channels were added to the manager
        assert NotificationChannel.CONSOLE in manager._channels
        assert NotificationChannel.EMAIL in manager._channels

        # Stop the manager
        await manager.stop()


@pytest.mark.asyncio
async def test_notification_manager_start_channel_error(notification_manager):
    """Test starting the notification service manager with a channel that fails to initialize."""
    # Mock the ConsoleNotificationChannel.initialize method to raise an exception
    with patch(
        "processpype.services.notification.channels.console.ConsoleNotificationChannel.initialize",
        new_callable=AsyncMock,
        side_effect=Exception("Initialization error"),
    ) as mock_initialize:
        # Mock the logger
        with patch.object(notification_manager, "_logger") as mock_logger:
            # Start the manager
            await notification_manager.start()

            # Check that the console channel was attempted to be initialized
            mock_initialize.assert_called_once()

            # Check that an error was logged
            mock_logger.error.assert_called_once_with(
                f"Failed to initialize {NotificationChannel.CONSOLE} channel: Initialization error"
            )

            # Check that the channel was not added to the manager
            assert NotificationChannel.CONSOLE not in notification_manager._channels

            # Stop the manager
            await notification_manager.stop()


@pytest.mark.asyncio
async def test_notification_manager_stop(notification_manager):
    """Test stopping the notification service manager."""
    # Mock the ConsoleNotificationChannel.initialize and shutdown methods
    with (
        patch(
            "processpype.services.notification.channels.console.ConsoleNotificationChannel.initialize",
            new_callable=AsyncMock,
        ),
        patch(
            "processpype.services.notification.channels.console.ConsoleNotificationChannel.shutdown",
            new_callable=AsyncMock,
        ) as mock_shutdown,
    ):
        # Start the manager
        await notification_manager.start()

        # Stop the manager
        await notification_manager.stop()

        # Check that the console channel was shut down
        mock_shutdown.assert_called_once()

        # Check that the channels were cleared
        assert not notification_manager._channels


@pytest.mark.asyncio
async def test_notification_manager_stop_channel_error(notification_manager):
    """Test stopping the notification service manager with a channel that fails to shut down."""
    # Mock the ConsoleNotificationChannel.initialize method
    with patch(
        "processpype.services.notification.channels.console.ConsoleNotificationChannel.initialize",
        new_callable=AsyncMock,
    ):
        # Start the manager
        await notification_manager.start()

        # Mock the ConsoleNotificationChannel.shutdown method to raise an exception
        with patch(
            "processpype.services.notification.channels.console.ConsoleNotificationChannel.shutdown",
            new_callable=AsyncMock,
            side_effect=Exception("Shutdown error"),
        ) as mock_shutdown:
            # Mock the logger
            with patch.object(notification_manager, "_logger") as mock_logger:
                # Stop the manager
                await notification_manager.stop()

                # Check that the console channel was attempted to be shut down
                mock_shutdown.assert_called_once()

                # Check that an error was logged
                mock_logger.error.assert_called_once_with(
                    f"Error shutting down {NotificationChannel.CONSOLE} channel: Shutdown error"
                )

                # Check that the channels were cleared
                assert not notification_manager._channels


@pytest.mark.asyncio
async def test_notification_manager_register_template(notification_manager):
    """Test registering a notification template."""
    # Create a template
    template = NotificationTemplate(
        name="test_template",
        template="Hello, {name}!",
        default_level=NotificationLevel.INFO,
    )

    # Register the template
    notification_manager.register_template(template)

    # Check that the template was registered
    assert "test_template" in notification_manager._templates
    assert notification_manager._templates["test_template"] is template


@pytest.mark.asyncio
async def test_notification_manager_notify(notification_manager):
    """Test sending a notification through the notification service manager."""
    # Mock the ConsoleNotificationChannel.initialize and send methods
    with (
        patch(
            "processpype.services.notification.channels.console.ConsoleNotificationChannel.initialize",
            new_callable=AsyncMock,
        ),
        patch(
            "processpype.services.notification.channels.console.ConsoleNotificationChannel.send",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        # Start the manager
        await notification_manager.start()

        # Send a notification
        await notification_manager.notify(
            message="Test notification",
            level=NotificationLevel.INFO,
        )

        # Check that the notification was sent to the console channel
        mock_send.assert_called_once()
        notification = mock_send.call_args[0][0]
        assert notification.message == "Test notification"
        assert notification.level == NotificationLevel.INFO

        # Stop the manager
        await notification_manager.stop()


@pytest.mark.asyncio
async def test_notification_manager_notify_with_template(notification_manager):
    """Test sending a notification with a template through the notification service manager."""
    # Mock the ConsoleNotificationChannel.initialize and send methods
    with (
        patch(
            "processpype.services.notification.channels.console.ConsoleNotificationChannel.initialize",
            new_callable=AsyncMock,
        ),
        patch(
            "processpype.services.notification.channels.console.ConsoleNotificationChannel.send",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        # Start the manager
        await notification_manager.start()

        # Register a template
        template = NotificationTemplate(
            name="test_template",
            template="Hello, {name}!",
            default_level=NotificationLevel.INFO,
        )
        notification_manager.register_template(template)

        # Send a notification with the template
        await notification_manager.notify_with_template(
            template_name="test_template",
            context={"name": "World"},
        )

        # Check that the notification was sent to the console channel
        mock_send.assert_called_once()
        notification = mock_send.call_args[0][0]
        assert notification.message == "Hello, World!"
        assert notification.level == NotificationLevel.INFO

        # Stop the manager
        await notification_manager.stop()


@pytest.mark.asyncio
async def test_notification_manager_notify_with_template_not_found(
    notification_manager,
):
    """Test sending a notification with a non-existent template."""
    # Start the manager
    await notification_manager.start()

    # Send a notification with a non-existent template
    with pytest.raises(
        ValueError, match="Notification template not found: non_existent_template"
    ):
        await notification_manager.notify_with_template(
            template_name="non_existent_template",
            context={"name": "World"},
        )

    # Stop the manager
    await notification_manager.stop()


@pytest.mark.asyncio
async def test_notification_manager_notify_specific_channels():
    """Test sending a notification to specific channels."""
    # Configure multiple channels
    config = NotificationConfiguration(
        enabled_channels=[
            NotificationChannel.CONSOLE,
            NotificationChannel.EMAIL,
        ],
        email_smtp_server="smtp.example.com",
        email_smtp_port=587,
        email_username="user@example.com",
        email_password="password",
        email_recipients=["recipient@example.com"],
        email_sender="sender@example.com",
    )

    # Create the manager
    logger = logging.getLogger("test_notification_manager")
    manager = NotificationServiceManager(config, logger)

    # Mock the channel initialize and send methods
    with (
        patch(
            "processpype.services.notification.channels.console.ConsoleNotificationChannel.initialize",
            new_callable=AsyncMock,
        ),
        patch(
            "processpype.services.notification.channels.email.EmailNotificationChannel.initialize",
            new_callable=AsyncMock,
        ),
        patch(
            "processpype.services.notification.channels.console.ConsoleNotificationChannel.send",
            new_callable=AsyncMock,
        ) as mock_console_send,
        patch(
            "processpype.services.notification.channels.email.EmailNotificationChannel.send",
            new_callable=AsyncMock,
        ) as mock_email_send,
    ):
        # Start the manager
        await manager.start()

        # Send a notification to only the email channel
        await manager.notify(
            message="Test notification",
            level=NotificationLevel.INFO,
            channels=[NotificationChannel.EMAIL],
        )

        # Check that the notification was sent to the email channel only
        mock_email_send.assert_called_once()
        mock_console_send.assert_not_called()

        # Reset the mocks
        mock_email_send.reset_mock()
        mock_console_send.reset_mock()

        # Send a notification to both channels
        await manager.notify(
            message="Test notification",
            level=NotificationLevel.INFO,
            channels=[NotificationChannel.CONSOLE, NotificationChannel.EMAIL],
        )

        # Check that the notification was sent to both channels
        mock_console_send.assert_called_once()
        mock_email_send.assert_called_once()

        # Stop the manager
        await manager.stop()
