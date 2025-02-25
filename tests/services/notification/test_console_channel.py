"""Tests for the console notification channel."""

import logging
from unittest.mock import patch

import pytest

from processpype.services.notification import Notification, NotificationLevel
from processpype.services.notification.channels.console import (
    ConsoleNotificationChannel,
)


@pytest.fixture
def console_channel():
    """Create a console notification channel for testing."""
    logger = logging.getLogger("test_console")
    return ConsoleNotificationChannel(logger)


@pytest.mark.asyncio
async def test_console_channel_initialization(console_channel):
    """Test initializing the console notification channel."""
    # Initialize the channel
    await console_channel.initialize()

    # No assertions needed, just checking that it doesn't raise an exception


@pytest.mark.asyncio
async def test_console_channel_shutdown(console_channel):
    """Test shutting down the console notification channel."""
    # Shutdown the channel
    await console_channel.shutdown()

    # No assertions needed, just checking that it doesn't raise an exception


@pytest.mark.asyncio
async def test_console_channel_send_info(console_channel):
    """Test sending an info notification to the console channel."""
    # Create a notification
    notification = Notification(
        message="Test info notification",
        level=NotificationLevel.INFO,
    )

    # Mock the logger
    with patch.object(console_channel._logger, "info") as mock_info:
        # Send the notification
        await console_channel.send(notification)

        # Check that the logger was called with the message and extra=None
        mock_info.assert_called_once_with("Test info notification", extra=None)


@pytest.mark.asyncio
async def test_console_channel_send_warning(console_channel):
    """Test sending a warning notification to the console channel."""
    # Create a notification
    notification = Notification(
        message="Test warning notification",
        level=NotificationLevel.WARNING,
    )

    # Mock the logger
    with patch.object(console_channel._logger, "warning") as mock_warning:
        # Send the notification
        await console_channel.send(notification)

        # Check that the logger was called with the message and extra=None
        mock_warning.assert_called_once_with("Test warning notification", extra=None)


@pytest.mark.asyncio
async def test_console_channel_send_error(console_channel):
    """Test sending an error notification to the console channel."""
    # Create a notification
    notification = Notification(
        message="Test error notification",
        level=NotificationLevel.ERROR,
    )

    # Mock the logger
    with patch.object(console_channel._logger, "error") as mock_error:
        # Send the notification
        await console_channel.send(notification)

        # Check that the logger was called with the message and extra=None
        mock_error.assert_called_once_with("Test error notification", extra=None)


@pytest.mark.asyncio
async def test_console_channel_send_critical(console_channel):
    """Test sending a critical notification to the console channel."""
    # Create a notification
    notification = Notification(
        message="Test critical notification",
        level=NotificationLevel.CRITICAL,
    )

    # Mock the logger
    with patch.object(console_channel._logger, "critical") as mock_critical:
        # Send the notification
        await console_channel.send(notification)

        # Check that the logger was called with the message and extra=None
        mock_critical.assert_called_once_with("Test critical notification", extra=None)


@pytest.mark.asyncio
async def test_console_channel_send_debug(console_channel):
    """Test sending a debug notification to the console channel."""
    # Create a notification
    notification = Notification(
        message="Test debug notification",
        level=NotificationLevel.DEBUG,
    )

    # Mock the logger
    with patch.object(console_channel._logger, "debug") as mock_debug:
        # Send the notification
        await console_channel.send(notification)

        # Check that the logger was called with the message and extra=None
        mock_debug.assert_called_once_with("Test debug notification", extra=None)


@pytest.mark.asyncio
async def test_console_channel_send_with_metadata(console_channel):
    """Test sending a notification with metadata to the console channel."""
    # Create a notification with metadata
    notification = Notification(
        message="Test notification with metadata",
        level=NotificationLevel.INFO,
        metadata={"key1": "value1", "key2": "value2"},
    )

    # Mock the logger
    with patch.object(console_channel._logger, "info") as mock_info:
        # Send the notification
        await console_channel.send(notification)

        # Check that the logger was called with the message and metadata
        mock_info.assert_called_once()
        args, kwargs = mock_info.call_args
        assert args[0] == "Test notification with metadata"
        assert kwargs["extra"] is not None
        assert kwargs["extra"]["metadata"] == {"key1": "value1", "key2": "value2"}
