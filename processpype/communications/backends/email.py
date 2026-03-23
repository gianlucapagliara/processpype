"""Email communicator backend using aiosmtplib."""

from __future__ import annotations

import logging
from email.message import EmailMessage
from typing import TYPE_CHECKING

import aiosmtplib

from processpype.communications.base import Communicator

if TYPE_CHECKING:
    from processpype.communications.models import OutgoingMessage
    from processpype.config.models import EmailCommunicatorConfig

logger = logging.getLogger(__name__)


class EmailCommunicator(Communicator):
    """Async email communicator (send-only)."""

    def __init__(self, name: str, config: EmailCommunicatorConfig) -> None:
        super().__init__(name, config)
        self._email_config = config
        self._smtp: aiosmtplib.SMTP | None = None

    @property
    def supports_receiving(self) -> bool:
        return False

    async def start(self) -> None:
        if self._started:
            return

        config = self._email_config
        self._smtp = aiosmtplib.SMTP(
            hostname=config.host,
            port=config.port,
            use_tls=config.use_tls,
        )
        await self._smtp.connect()

        if config.start_tls and not config.use_tls:
            await self._smtp.starttls()

        if config.username and config.password:
            await self._smtp.login(config.username, config.password)

        self._started = True
        logger.info("Email communicator '%s' started", self._name)

    async def stop(self) -> None:
        if self._smtp:
            try:
                await self._smtp.quit()
            except Exception:
                logger.debug("SMTP quit failed (connection may already be closed)")
            self._smtp = None
        self._started = False

    async def send(self, message: OutgoingMessage) -> None:
        if not self._smtp:
            logger.warning("Email communicator '%s' not started, skipping", self._name)
            return

        config = self._email_config
        recipients = message.metadata.get("recipients", config.default_recipients)
        if not recipients:
            logger.warning("No recipients for email message, skipping")
            return

        msg = EmailMessage()
        msg["From"] = config.from_address
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = (
            message.subject or f"[{message.severity.value.upper()}] Notification"
        )
        msg.set_content(message.message)

        try:
            await self._smtp.send_message(msg)
        except (aiosmtplib.SMTPServerDisconnected, ConnectionError):
            logger.info("SMTP connection lost, reconnecting")
            try:
                await self._reconnect()
                await self._smtp.send_message(msg)
            except Exception:
                logger.exception(
                    "Email send failed after reconnect attempt, dropping message"
                )

    async def _reconnect(self) -> None:
        """Reconnect to SMTP server."""
        if self._smtp:
            try:
                await self._smtp.quit()
            except Exception:
                pass
        self._started = False
        await self.start()
