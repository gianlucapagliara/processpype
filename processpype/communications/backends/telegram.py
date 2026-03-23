"""Telegram communicator backend using Telethon."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from telethon import TelegramClient
from telethon.events import NewMessage
from telethon.sessions import StringSession
from telethon.tl.custom import Message

from processpype.communications.base import Communicator
from processpype.communications.models import IncomingMessage, OutgoingMessage
from processpype.config.models import TelegramChatConfig, TelegramCommunicatorConfig

logger = logging.getLogger(__name__)


def _divide_chunks(lst: list[Any], n: int = 30) -> list[list[Any]]:
    """Break a list into chunks of size n."""
    return [lst[i : i + n] for i in range(0, len(lst), n)]


class TelegramCommunicator(Communicator):
    """Telegram bot communicator with send and optional receive support.

    Outgoing messages are queued and drained by a background task to
    respect Telegram rate limits. Incoming messages (when enabled) are
    routed through the dispatcher's event publisher.
    """

    MAX_QUEUE_SIZE = 1000
    """Maximum number of queued messages before dropping new ones."""

    def __init__(self, name: str, config: TelegramCommunicatorConfig) -> None:
        super().__init__(name, config)
        self._telegram_config = config
        self._chats: dict[str, TelegramChatConfig] = dict(config.chats)
        self._bot: TelegramClient | None = None
        self._msg_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue(
            maxsize=self.MAX_QUEUE_SIZE
        )
        self._drain_task: asyncio.Task[None] | None = None
        self._listen_task: asyncio.Task[None] | None = None

    @property
    def supports_receiving(self) -> bool:
        return self._telegram_config.listen_to_commands

    async def start(self) -> None:
        if self._started:
            return

        config = self._telegram_config
        session: StringSession | str
        if config.session_string:
            session = StringSession(config.session_string)
        elif config.listen_to_commands:
            # Persistent file session for listening bots
            session = f".telegram_session_{self._name}"
        else:
            session = StringSession()  # Ephemeral for send-only

        self._bot = TelegramClient(session, config.api_id, config.api_hash)
        await self._bot.start(bot_token=config.token if config.token else None)

        if self.supports_receiving:
            self._bot.add_event_handler(self._on_new_message, event=NewMessage)
            self._listen_task = asyncio.create_task(
                self._bot.run_until_disconnected(),
                name=f"telegram-listen-{self._name}",
            )
            logger.info("Telegram communicator '%s' listening for messages", self._name)

        self._drain_task = asyncio.create_task(
            self._drain_queue(),
            name=f"telegram-drain-{self._name}",
        )

        self._started = True
        logger.info("Telegram communicator '%s' started", self._name)

    async def stop(self) -> None:
        if self._drain_task:
            self._drain_task.cancel()
            self._drain_task = None
        if self._listen_task:
            self._listen_task.cancel()
            self._listen_task = None
        if self._bot and self._bot.is_connected():
            await self._bot.disconnect()
            self._bot = None
        self._started = False

    async def send(self, message: OutgoingMessage) -> None:
        """Queue an outgoing message for sending."""
        lines = message.message.split("\n")
        chunks = _divide_chunks(lines, 30)
        for chunk in chunks:
            try:
                self._msg_queue.put_nowait(("\n".join(chunk), message.label))
            except asyncio.QueueFull:
                logger.warning(
                    "Telegram message queue full (%d), dropping message chunk",
                    self.MAX_QUEUE_SIZE,
                )

    # --- Internal ---

    async def _drain_queue(self) -> None:
        """Background task that sends queued messages."""
        while True:
            try:
                text, label = await self._msg_queue.get()
                if text:
                    await self._send_with_retry(text, label)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Unexpected error in drain loop")
            await asyncio.sleep(0.1)

    async def _ensure_connected(self) -> None:
        """Reconnect to Telegram if the client has disconnected."""
        if self._bot and not self._bot.is_connected():
            logger.warning("Telegram client disconnected, attempting reconnect")
            try:
                await self._bot.connect()
            except Exception:
                logger.exception("Telegram reconnect failed")
                raise

    async def _send_with_retry(
        self, text: str, label: str, max_retries: int = 3
    ) -> None:
        """Send a message with exponential backoff retry."""
        await self._ensure_connected()
        for attempt in range(max_retries):
            try:
                await self._send_to_chat(text, label)
                return
            except Exception:
                if attempt == max_retries - 1:
                    logger.error(
                        "Failed to send after %d attempts, dropping message",
                        max_retries,
                    )
                    return
                wait = 2**attempt
                logger.warning(
                    "Send failed (attempt %d/%d), retrying in %ds",
                    attempt + 1,
                    max_retries,
                    wait,
                )
                await asyncio.sleep(wait)

    async def _send_to_chat(self, text: str, label: str) -> None:
        """Send a message to the chat configured for the given label."""
        if not self._bot:
            return

        chat_config = self._chats.get(label)
        if chat_config is None:
            chat_config = self._chats.get("default")
        if chat_config is None:
            logger.warning(
                "No chat config for label '%s' and no default configured", label
            )
            return
        if not chat_config.active:
            return

        formatted = f"\n{text}\n"
        await self._bot.send_message(
            entity=chat_config.chat_id,
            message=formatted,
            reply_to=chat_config.topic_id,
            parse_mode="html",
        )

    async def _on_new_message(self, event: NewMessage.Event) -> None:
        """Handle incoming Telegram messages."""
        if not self._on_incoming:
            return

        if not self._is_authorized(event):
            logger.info("Rejected unauthorized message from chat %s", event.chat_id)
            return

        chat_label = self._resolve_chat_label(event)

        try:
            incoming = IncomingMessage(
                text=event.message.raw_text or "",
                sender=await self._get_sender_name(event),
                sender_id=str(event.sender_id) if event.sender_id else None,
                chat_label=chat_label,
                backend_name=self._name,
                timestamp=self._get_message_date(event),
                raw_event=event,
            )
            self._on_incoming(incoming)
        except Exception:
            logger.exception("Error handling incoming Telegram message")

    def _is_authorized(self, event: NewMessage.Event) -> bool:
        """Check if the message comes from an authorized chat/topic."""
        for chat_config in self._chats.values():
            if not chat_config.command_authorized:
                continue
            if str(event.chat_id) != chat_config.chat_id:
                continue
            if chat_config.topic_id is not None:
                if (
                    event.message.reply_to is None
                    or chat_config.topic_id != event.message.reply_to.reply_to_msg_id
                ):
                    continue
            return True
        return False

    def _resolve_chat_label(self, event: NewMessage.Event) -> str:
        """Find the label for the chat that received this message."""
        for label, chat_config in self._chats.items():
            if str(event.chat_id) != chat_config.chat_id:
                continue
            if chat_config.topic_id is not None:
                if (
                    event.message.reply_to is not None
                    and chat_config.topic_id == event.message.reply_to.reply_to_msg_id
                ):
                    return label
            else:
                return label
        return "default"

    @staticmethod
    async def _get_sender_name(event: NewMessage.Event | Message) -> str | None:
        sender = await event.get_sender()
        return sender.username if sender else None

    @staticmethod
    def _get_message_date(event: NewMessage.Event | Message) -> datetime | None:
        source = event
        if hasattr(event, "forward") and event.forward is not None:
            source = event.forward
        return source.date  # type: ignore[no-any-return]
