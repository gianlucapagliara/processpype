"""Email notification channel implementation."""

import logging
from datetime import datetime
from email.message import EmailMessage

import aiosmtplib

from ..models import Notification, NotificationConfiguration


class EmailNotificationChannel:
    """Email notification channel.

    This channel sends notifications via email using SMTP.
    """

    def __init__(self, config: NotificationConfiguration, logger: logging.Logger):
        """Initialize the email notification channel.

        Args:
            config: Notification service configuration
            logger: Logger instance for notifications
        """
        self._logger = logger
        self._config = config
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the email notification channel.

        Validates the email configuration.
        """
        if not self._config.email_smtp_server:
            self._logger.warning(
                "SMTP server not configured, email channel will be disabled"
            )
            return

        if not self._config.email_recipients:
            self._logger.warning(
                "No email recipients configured, email channel will be disabled"
            )
            return

        if not self._config.email_sender:
            self._logger.warning(
                "Email sender not configured, email channel will be disabled"
            )
            return

        # Test connection to SMTP server
        try:
            smtp = aiosmtplib.SMTP(
                hostname=self._config.email_smtp_server,
                port=self._config.email_smtp_port,
            )
            await smtp.connect()

            # If credentials are provided, try to authenticate
            if self._config.email_username and self._config.email_password:
                await smtp.login(
                    self._config.email_username, self._config.email_password
                )

            await smtp.quit()
            self._initialized = True
            self._logger.debug("Email notification channel initialized")
        except Exception as e:
            self._logger.error(f"Failed to initialize email channel: {str(e)}")

    async def shutdown(self) -> None:
        """Shutdown the email notification channel.

        This is a no-op for the email channel.
        """
        self._logger.debug("Email notification channel shutdown")

    async def send(self, notification: Notification) -> None:
        """Send a notification via email.

        Args:
            notification: The notification to send
        """
        if not self._initialized:
            self._logger.warning("Email channel not initialized, skipping notification")
            return

        if not self._config.email_recipients:
            self._logger.warning(
                "No email recipients configured, skipping notification"
            )
            return

        # Create email message
        message = EmailMessage()
        message["From"] = self._config.email_sender
        message["To"] = ", ".join(self._config.email_recipients)
        message["Subject"] = f"[{notification.level.upper()}] Notification"

        # Format the message body
        body = notification.message

        # Add metadata if available
        if notification.metadata:
            body += "\n\nMetadata:\n"
            for key, value in notification.metadata.items():
                body += f"- {key}: {value}\n"

        # Add timestamp
        timestamp = notification.timestamp or datetime.now().isoformat()
        body += f"\n\nTimestamp: {timestamp}"

        message.set_content(body)

        # Send the email
        try:
            smtp = aiosmtplib.SMTP(
                hostname=self._config.email_smtp_server,
                port=self._config.email_smtp_port,
            )
            await smtp.connect()

            # If credentials are provided, authenticate
            if self._config.email_username and self._config.email_password:
                await smtp.login(
                    self._config.email_username, self._config.email_password
                )

            await smtp.send_message(message)
            await smtp.quit()
            self._logger.debug(
                f"Sent email notification to {len(self._config.email_recipients)} recipients"
            )
        except Exception as e:
            self._logger.error(f"Error sending email notification: {str(e)}")
