"""Tests for the email notification channel."""

import logging
from unittest.mock import AsyncMock, patch

import pytest

from processpype.services.notification import (
    Notification,
    NotificationChannel,
    NotificationConfiguration,
    NotificationLevel,
)
from processpype.services.notification.channels.email import EmailNotificationChannel


@pytest.fixture
def email_config():
    """Create an email channel configuration for testing."""
    return NotificationConfiguration(
        enabled_channels=[NotificationChannel.EMAIL],
        default_level=NotificationLevel.INFO,
        email_smtp_server="smtp.example.com",
        email_smtp_port=587,
        email_username="user@example.com",
        email_password="password",
        email_recipients=["recipient@example.com"],
        email_sender="sender@example.com",
    )


@pytest.fixture
def email_channel(email_config):
    """Create an email notification channel for testing."""
    logger = logging.getLogger("test_email")
    return EmailNotificationChannel(email_config, logger)


@pytest.mark.asyncio
async def test_email_channel_initialization(email_channel):
    """Test initializing the email notification channel."""
    # Mock the SMTP client
    with patch(
        "processpype.services.notification.channels.email.aiosmtplib.SMTP",
        autospec=True,
    ) as mock_smtp_class:
        # Mock the client instance
        mock_smtp = AsyncMock()
        mock_smtp_class.return_value = mock_smtp

        # Initialize the channel
        await email_channel.initialize()

        # Check that the SMTP client was created with the correct parameters
        mock_smtp_class.assert_called_once_with(
            hostname=email_channel._config.email_smtp_server,
            port=email_channel._config.email_smtp_port,
        )

        # Check that the client was connected and authenticated
        mock_smtp.connect.assert_called_once()
        mock_smtp.login.assert_called_once_with(
            email_channel._config.email_username,
            email_channel._config.email_password,
        )

        # Check that the client was initialized
        assert email_channel._initialized is True


@pytest.mark.asyncio
async def test_email_channel_initialization_no_server(email_channel):
    """Test initializing the email channel with no SMTP server."""
    # Create a new config with no SMTP server
    config_no_server = NotificationConfiguration(
        enabled_channels=[NotificationChannel.EMAIL],
        default_level=NotificationLevel.INFO,
        email_smtp_server=None,
        email_recipients=["recipient@example.com"],
        email_sender="sender@example.com",
    )

    # Create a new channel with the modified config
    logger = logging.getLogger("test_email")
    channel = EmailNotificationChannel(config_no_server, logger)

    # Mock the logger
    with patch.object(channel, "_logger") as mock_logger:
        # Initialize the channel
        await channel.initialize()

        # Check that a warning was logged
        mock_logger.warning.assert_called_once_with(
            "SMTP server not configured, email channel will be disabled"
        )

        # Check that the client was not initialized
        assert channel._initialized is False


@pytest.mark.asyncio
async def test_email_channel_initialization_no_recipients(email_channel):
    """Test initializing the email channel with no recipients."""
    # Create a new config with no recipients
    config_no_recipients = NotificationConfiguration(
        enabled_channels=[NotificationChannel.EMAIL],
        default_level=NotificationLevel.INFO,
        email_smtp_server="smtp.example.com",
        email_smtp_port=587,
        email_username="user@example.com",
        email_password="password",
        email_recipients=[],
        email_sender="sender@example.com",
    )

    # Create a new channel with the modified config
    logger = logging.getLogger("test_email")
    channel = EmailNotificationChannel(config_no_recipients, logger)

    # Mock the logger
    with patch.object(channel, "_logger") as mock_logger:
        # Initialize the channel
        await channel.initialize()

        # Check that a warning was logged
        mock_logger.warning.assert_called_once_with(
            "No email recipients configured, email channel will be disabled"
        )

        # Check that the client was not initialized
        assert channel._initialized is False


@pytest.mark.asyncio
async def test_email_channel_initialization_no_sender(email_channel):
    """Test initializing the email channel with no sender."""
    # Create a new config with no sender
    config_no_sender = NotificationConfiguration(
        enabled_channels=[NotificationChannel.EMAIL],
        default_level=NotificationLevel.INFO,
        email_smtp_server="smtp.example.com",
        email_smtp_port=587,
        email_username="user@example.com",
        email_password="password",
        email_recipients=["recipient@example.com"],
        email_sender=None,
    )

    # Create a new channel with the modified config
    logger = logging.getLogger("test_email")
    channel = EmailNotificationChannel(config_no_sender, logger)

    # Mock the logger
    with patch.object(channel, "_logger") as mock_logger:
        # Initialize the channel
        await channel.initialize()

        # Check that a warning was logged
        mock_logger.warning.assert_called_once_with(
            "Email sender not configured, email channel will be disabled"
        )

        # Check that the client was not initialized
        assert channel._initialized is False


@pytest.mark.asyncio
async def test_email_channel_initialization_no_credentials(email_channel):
    """Test initializing the email channel with no credentials."""
    # Create a new config with no credentials
    config_no_credentials = NotificationConfiguration(
        enabled_channels=[NotificationChannel.EMAIL],
        default_level=NotificationLevel.INFO,
        email_smtp_server="smtp.example.com",
        email_smtp_port=587,
        email_username=None,
        email_password=None,
        email_recipients=["recipient@example.com"],
        email_sender="sender@example.com",
    )

    # Create a new channel with the modified config
    logger = logging.getLogger("test_email")
    channel = EmailNotificationChannel(config_no_credentials, logger)

    # Mock the SMTP client
    with patch(
        "processpype.services.notification.channels.email.aiosmtplib.SMTP",
        autospec=True,
    ) as mock_smtp_class:
        # Mock the client instance
        mock_smtp = AsyncMock()
        mock_smtp_class.return_value = mock_smtp

        # Initialize the channel
        await channel.initialize()

        # Check that the SMTP client was created
        mock_smtp_class.assert_called_once()

        # Check that the client was connected but not authenticated
        mock_smtp.connect.assert_called_once()
        mock_smtp.login.assert_not_called()

        # Check that the client was initialized
        assert channel._initialized is True


@pytest.mark.asyncio
async def test_email_channel_initialization_connection_error(email_channel):
    """Test handling connection errors when initializing the email channel."""
    # Mock the SMTP client to raise an exception
    with patch(
        "processpype.services.notification.channels.email.aiosmtplib.SMTP",
        autospec=True,
    ) as mock_smtp_class:
        # Mock the client instance
        mock_smtp = AsyncMock()
        mock_smtp.connect.side_effect = Exception("Connection error")
        mock_smtp_class.return_value = mock_smtp

        # Mock the logger
        with patch.object(email_channel, "_logger") as mock_logger:
            # Initialize the channel
            await email_channel.initialize()

            # Check that an error was logged
            mock_logger.error.assert_called_once_with(
                "Failed to initialize email channel: Connection error"
            )

            # Check that the client was not initialized
            assert email_channel._initialized is False


@pytest.mark.asyncio
async def test_email_channel_shutdown(email_channel):
    """Test shutting down the email notification channel."""
    # No need to test anything specific for shutdown as it's a no-op
    await email_channel.shutdown()


@pytest.mark.asyncio
async def test_email_channel_send(email_channel):
    """Test sending a notification through the email channel."""
    # Create a notification
    notification = Notification(
        message="Test notification",
        level=NotificationLevel.INFO,
        metadata={"key": "value"},
    )

    # Set the channel as initialized
    email_channel._initialized = True

    # Mock the SMTP client
    with patch(
        "processpype.services.notification.channels.email.aiosmtplib.SMTP",
        autospec=True,
    ) as mock_smtp_class:
        # Mock the client instance
        mock_smtp = AsyncMock()
        mock_smtp_class.return_value = mock_smtp

        # Send the notification
        await email_channel.send(notification)

        # Check that the SMTP client was created
        mock_smtp_class.assert_called_once()

        # Check that the client was connected and authenticated
        mock_smtp.connect.assert_called_once()
        mock_smtp.login.assert_called_once()

        # Check that send_message was called
        mock_smtp.send_message.assert_called_once()

        # Check that quit was called
        mock_smtp.quit.assert_called_once()


@pytest.mark.asyncio
async def test_email_channel_send_no_initialized(email_channel):
    """Test sending a notification when the channel is not initialized."""
    # Create a notification
    notification = Notification(
        message="Test notification",
        level=NotificationLevel.INFO,
    )

    # Ensure the channel is not initialized
    email_channel._initialized = False

    # Mock the logger
    with patch.object(email_channel, "_logger") as mock_logger:
        # Send the notification
        await email_channel.send(notification)

        # Check that a warning was logged
        mock_logger.warning.assert_called_once_with(
            "Email channel not initialized, skipping notification"
        )


@pytest.mark.asyncio
async def test_email_channel_send_error(email_channel):
    """Test handling errors when sending a notification."""
    # Create a notification
    notification = Notification(
        message="Test notification",
        level=NotificationLevel.INFO,
    )

    # Set the channel as initialized
    email_channel._initialized = True

    # Mock the SMTP client to raise an exception
    with patch(
        "processpype.services.notification.channels.email.aiosmtplib.SMTP",
        autospec=True,
    ) as mock_smtp_class:
        # Mock the client instance
        mock_smtp = AsyncMock()
        mock_smtp.send_message.side_effect = Exception("Send error")
        mock_smtp_class.return_value = mock_smtp

        # Mock the logger
        with patch.object(email_channel, "_logger") as mock_logger:
            # Send the notification
            await email_channel.send(notification)

            # Check that an error was logged
            mock_logger.error.assert_called_once_with(
                "Error sending email notification: Send error"
            )
