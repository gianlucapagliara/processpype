"""Console notification channel implementation."""

import logging

from ..models import Notification, NotificationLevel


class ConsoleNotificationChannel:
    """Console notification channel.

    This channel outputs notifications to the console using the logger.
    """

    def __init__(self, logger: logging.Logger):
        """Initialize the console notification channel.

        Args:
            logger: Logger instance for notifications
        """
        self._logger = logger

    async def send(self, notification: Notification) -> None:
        """Send a notification to the console.

        Args:
            notification: The notification to send
        """
        # Map notification level to logger method
        level_map = {
            NotificationLevel.DEBUG: self._logger.debug,
            NotificationLevel.INFO: self._logger.info,
            NotificationLevel.WARNING: self._logger.warning,
            NotificationLevel.ERROR: self._logger.error,
            NotificationLevel.CRITICAL: self._logger.critical,
        }

        # Get the appropriate logger method
        log_method = level_map.get(notification.level, self._logger.info)

        # Add metadata as extra context if available
        extra = {}
        if notification.metadata:
            extra["metadata"] = notification.metadata

        # Log the message
        log_method(notification.message, extra=extra if extra else None)

    async def initialize(self) -> None:
        """Initialize the console notification channel.

        This is a no-op for the console channel.
        """
        self._logger.debug("Console notification channel initialized")

    async def shutdown(self) -> None:
        """Shutdown the console notification channel.

        This is a no-op for the console channel.
        """
        self._logger.debug("Console notification channel shutdown")
