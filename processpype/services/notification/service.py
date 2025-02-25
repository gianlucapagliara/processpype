"""Notification service implementation."""

import datetime
import logging
from collections.abc import Callable
from typing import Any, cast

from processpype.core.service.manager import ServiceManager
from processpype.core.service.service import Service

from .channels import ConsoleNotificationChannel, EmailNotificationChannel
from .models import (
    Notification,
    NotificationChannel,
    NotificationConfiguration,
    NotificationLevel,
    NotificationTemplate,
)


class NotificationServiceManager(ServiceManager):
    """Manager for the NotificationService."""

    def __init__(
        self,
        config: NotificationConfiguration,
        logger: logging.Logger,
    ):
        """Initialize the notification service manager.

        Args:
            config: Notification service configuration
            logger: Logger instance for service operations
        """
        super().__init__(logger)
        self._config = config
        self._channels: dict[NotificationChannel, Any] = {}
        self._templates: dict[str, NotificationTemplate] = {}

    async def start(self) -> None:
        """Start the notification service.

        Initializes the configured notification channels.
        """
        self.logger.info("Starting notification service")

        # Initialize channels based on configuration
        for channel_type in self._config.enabled_channels:
            if channel_type == NotificationChannel.CONSOLE:
                self._channels[channel_type] = ConsoleNotificationChannel(self.logger)
            elif channel_type == NotificationChannel.TELEGRAM:
                pass
            elif channel_type == NotificationChannel.EMAIL:
                self._channels[channel_type] = EmailNotificationChannel(
                    self._config, self.logger
                )
            else:
                self.logger.warning(
                    f"Unknown notification channel type: {channel_type}"
                )
                continue

            # Initialize the channel
            try:
                await self._channels[channel_type].initialize()
                self.logger.info(f"Initialized {channel_type} notification channel")
            except Exception as e:
                self.logger.error(
                    f"Failed to initialize {channel_type} channel: {str(e)}"
                )
                del self._channels[channel_type]

        # Register default templates
        self.register_template(
            NotificationTemplate(
                name="service_status",
                template="Service {service_name} status changed to {status}",
                default_level=NotificationLevel.INFO,
            )
        )

        self.register_template(
            NotificationTemplate(
                name="error",
                template="Error: {message}",
                default_level=NotificationLevel.ERROR,
            )
        )

        self.logger.info(
            f"Notification service started with {len(self._channels)} channels"
        )

    async def stop(self) -> None:
        """Stop the notification service.

        Shuts down all notification channels.
        """
        self.logger.info("Stopping notification service")

        # Shutdown all channels
        for channel_type, channel in self._channels.items():
            try:
                await channel.shutdown()
                self.logger.info(f"Shut down {channel_type} notification channel")
            except Exception as e:
                self.logger.error(
                    f"Error shutting down {channel_type} channel: {str(e)}"
                )

        self._channels.clear()
        self.logger.info("Notification service stopped")

    def register_template(self, template: NotificationTemplate) -> None:
        """Register a notification template.

        Args:
            template: The template to register
        """
        self._templates[template.name] = template
        self.logger.debug(f"Registered notification template: {template.name}")

    async def notify(
        self,
        message: str,
        level: NotificationLevel | None = None,
        channels: list[NotificationChannel] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Send a notification to configured channels.

        Args:
            message: The notification message
            level: The notification level (defaults to configuration default)
            channels: Specific channels to send to (defaults to all enabled)
            metadata: Additional metadata to include with the notification
        """
        # Use default level if not specified
        if level is None:
            level = self._config.default_level

        # Create notification object
        notification = Notification(
            message=message,
            level=level,
            metadata=metadata,
            timestamp=datetime.datetime.now().isoformat(),
        )

        # Determine which channels to use
        target_channels = channels or list(self._channels.keys())

        # Send to each channel
        for channel_type in target_channels:
            channel = self._channels.get(channel_type)
            if not channel:
                self.logger.warning(
                    f"Channel {channel_type} not available, skipping notification"
                )
                continue

            try:
                await channel.send(notification)
            except Exception as e:
                self.logger.error(
                    f"Error sending notification to {channel_type}: {str(e)}"
                )

    async def notify_with_template(
        self,
        template_name: str,
        context: dict[str, Any],
        level: NotificationLevel | None = None,
        channels: list[NotificationChannel] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Send a notification using a template.

        Args:
            template_name: The name of the template to use
            context: Context variables for the template
            level: The notification level (defaults to template default)
            channels: Specific channels to send to (defaults to all enabled)
            metadata: Additional metadata to include with the notification

        Raises:
            ValueError: If the template does not exist
        """
        # Get the template
        template = self._templates.get(template_name)
        if not template:
            raise ValueError(f"Notification template not found: {template_name}")

        # Render the template
        message = template.render(context)

        # Use template default level if not specified
        if level is None:
            level = template.default_level

        # Send the notification
        await self.notify(message, level, channels, metadata)

    def add_telegram_message_handler(self, handler: Callable) -> None:
        """Add a handler for incoming Telegram messages.

        Args:
            handler: Callback function that will be called when a message is received.
                    The function should accept (event) as parameter.
        """
        telegram_channel = self._channels.get(NotificationChannel.TELEGRAM)
        if not telegram_channel:
            self.logger.warning(
                "Telegram channel not available, can't add message handler"
            )
            return

        if not hasattr(telegram_channel, "add_message_handler"):
            self.logger.warning("Telegram channel doesn't support message handlers")
            return

        telegram_channel.add_message_handler(handler)


class NotificationService(Service):
    """Service for sending notifications."""

    configuration_class = NotificationConfiguration

    def create_manager(self) -> ServiceManager:
        """Create the notification service manager.

        Returns:
            A new NotificationServiceManager instance
        """
        return NotificationServiceManager(
            cast(NotificationConfiguration, self.config),
            self.logger,
        )

    @property
    def manager(self) -> NotificationServiceManager:
        """Get the notification service manager.

        Returns:
            The notification service manager
        """
        return cast(NotificationServiceManager, super().manager)

    async def notify(
        self,
        message: str,
        level: NotificationLevel | None = None,
        channels: list[NotificationChannel] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Send a notification to configured channels.

        Args:
            message: The notification message
            level: The notification level (defaults to configuration default)
            channels: Specific channels to send to (defaults to all enabled)
            metadata: Additional metadata to include with the notification
        """
        await self.manager.notify(message, level, channels, metadata)

    async def notify_with_template(
        self,
        template_name: str,
        context: dict[str, Any],
        level: NotificationLevel | None = None,
        channels: list[NotificationChannel] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Send a notification using a template.

        Args:
            template_name: The name of the template to use
            context: Context variables for the template
            level: The notification level (defaults to template default)
            channels: Specific channels to send to (defaults to all enabled)
            metadata: Additional metadata to include with the notification

        Raises:
            ValueError: If the template does not exist
        """
        await self.manager.notify_with_template(
            template_name, context, level, channels, metadata
        )

    def register_template(self, template: NotificationTemplate) -> None:
        """Register a notification template.

        Args:
            template: The template to register
        """
        self.manager.register_template(template)

    def add_telegram_message_handler(self, handler: Callable) -> None:
        """Add a handler for incoming Telegram messages.

        Args:
            handler: Callback function that will be called when a message is received.
                    The function should accept (event) as parameter.
        """
        self.manager.add_telegram_message_handler(handler)
