"""Telegram notification bot using telethon.

Requires: telethon (``pip install processpype[telegram]``)
"""

import asyncio
import logging
import os
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, NamedTuple

from telethon import TelegramClient, functions
from telethon.events import NewMessage
from telethon.sessions import StringSession
from telethon.tl.custom import Message

from processpype.notifications.base import NotifierBase

logger = logging.getLogger(__name__)


def _safe_ensure_future(
    coro: Any, loop: asyncio.AbstractEventLoop | None = None
) -> asyncio.Task[Any]:
    """Schedule a coroutine on the event loop with error logging."""
    task: asyncio.Task[Any] = asyncio.ensure_future(coro)

    def _handle_exception(t: asyncio.Task[Any]) -> None:
        if t.cancelled():
            return
        exc = t.exception()
        if exc:
            logger.error(f"Unhandled exception in background task: {exc}", exc_info=exc)

    task.add_done_callback(_handle_exception)
    return task


def _get_temp_folder() -> str:
    project_dir = os.environ.get("PROJECT_DIR", os.getcwd())
    return os.path.join(project_dir, ".temp")


def authorized_only(
    handler: Callable[[Any, NewMessage.Event], Awaitable[Any]],
) -> Callable[..., Any]:
    """Decorator to check if the message comes from an authorized chat."""

    async def wrapper(self: Any, event: NewMessage.Event) -> Any:
        for chat_config in self._chat_configs.values():
            if not chat_config.command_authorized:
                continue
            if event.chat_id != chat_config.chat_id:
                continue
            if chat_config.topic_id is not None and (
                event.message.reply_to is None
                or (chat_config.topic_id != event.message.reply_to.reply_to_msg_id)
            ):
                continue
            try:
                return await handler(self, event)
            except Exception as e:
                logger.exception(f"Exception in Telegram handler: {e}")
        logger.info("Rejected unauthorized message from: %s", event.chat_id)
        return None

    return wrapper


class TelegramMessage(NamedTuple):
    text: str
    chat_label: str


@dataclass
class ChatConfiguration:
    label: str
    chat_id: str
    topic_id: str | None = None
    offset: int = 0
    end: int = 0
    destinations: list[int] | None = None
    command_authorized: bool = False
    active: bool = True

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ChatConfiguration":
        return ChatConfiguration(
            d["label"],
            d["chat_id"],
            topic_id=d.get("topic_id"),
            offset=d.get("offset", 0),
            end=d.get("end", 0),
            destinations=d.get("destinations"),
            command_authorized=d.get("command_authorized", False),
            active=d.get("active", True),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "chat_id": self.chat_id,
            "topic_id": self.topic_id,
            "offset": self.offset,
            "end": self.end,
            "destinations": self.destinations,
            "command_authorized": self.command_authorized,
            "active": self.active,
        }


class TelegramBot(NotifierBase):
    """Async Telegram notifier using telethon."""

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        token: str,
        chat_configs: list[ChatConfiguration],
        commands_handle: Callable[..., Any],
        listen_to_commands: bool = False,
        session_string: str | None = None,
    ) -> None:
        super().__init__()

        self._chat_configs: dict[str, ChatConfiguration] = {}
        self.chat_configurations = chat_configs
        if "default" not in self._chat_configs:
            raise ValueError("No default chat configuration found.")

        self._commands_handle = commands_handle
        self._listen_to_commands = listen_to_commands

        self.session_file: str | None = None
        temp_folder = _get_temp_folder()
        if session_string:
            session: str | StringSession = StringSession(session_string)
        elif not listen_to_commands:
            session = os.path.join(
                temp_folder, f"sending_bot_{random.randint(1, int(1e12))}"
            )
            self.session_file = session
        else:
            session = os.path.join(temp_folder, "listening_bot")
            self.session_file = session

        self._bot = TelegramClient(session, api_id, api_hash)
        self._token = token

        if self._listen_to_commands:
            self._bot.add_event_handler(self.new_message_handler, event=NewMessage)

        self._msg_queue: asyncio.Queue[TelegramMessage] = asyncio.Queue()
        self._ev_loop = asyncio.get_event_loop()
        self._listen_msg_task: asyncio.Task[Any] | None = None
        self._send_msg_task: asyncio.Task[Any] | None = None
        self._reply_markup = None

    @property
    def chat_configurations(self) -> list[ChatConfiguration]:
        return list(self._chat_configs.values())

    @chat_configurations.setter
    def chat_configurations(self, chat_configs: list[ChatConfiguration]) -> None:
        self._chat_configs = {c.label: c for c in chat_configs}

    @property
    def client(self) -> TelegramClient:
        return self._bot

    async def start(self) -> None:
        if not self._started:
            self._started = True
            await self._bot.start(bot_token=self._token if self._token else None)
            if self._listen_to_commands:
                self._listen_msg_task = _safe_ensure_future(
                    self._bot.run_until_disconnected()
                )
                logger.info("Telegram is listening...")
            self._send_msg_task = _safe_ensure_future(self.send_msg_from_queue())

    async def stop(self) -> None:
        if self._listen_msg_task:
            self._listen_msg_task.cancel()
        if self._send_msg_task:
            self._send_msg_task.cancel()
        if self._started or self._bot.is_connected:
            await self._bot.disconnect()
            self._started = False
        if self.session_file and os.path.exists(self.session_file):
            os.remove(self.session_file)

    def add_chat_configuration(self, chat_config: ChatConfiguration) -> None:
        self._chat_configs[chat_config.label] = chat_config

    @authorized_only
    async def new_message_handler(self, event: NewMessage.Event) -> None:
        try:
            input_text = self.get_text_from_update(event, include_html=False)
            sender = await self.get_sender_name_from_update(event, include_forward=True)
            sender = "Unknown" if sender is None else sender
            chat = await self.get_chat_title_from_update(event, include_forward=False)
            forwarded_from = await self.get_chat_title_from_update(
                event, include_forward=True
            )
            forwarded_from = (
                f" (from {forwarded_from})" if forwarded_from != chat else ""
            )
            logger.info(f"[Message][{sender} on {chat}{forwarded_from}]: {input_text}")
            await self._commands_handle(event)
        except Exception as e:
            self.add_msg_to_queue(str(e), "default")

    @staticmethod
    def _divide_chunks(arr: list[Any], n: int = 5) -> Any:
        for i in range(0, len(arr), n):
            yield arr[i : i + n]

    def add_msg_to_queue(self, msg: str, label: str = "default", **kwargs: Any) -> None:
        lines: list[str] = msg.split("\n")
        msg_chunks = self._divide_chunks(lines, 30)
        for chunk in msg_chunks:
            self._msg_queue.put_nowait(TelegramMessage("\n".join(chunk), label))

    async def send_msg_from_queue(self) -> None:
        while True:
            try:
                new_msg: TelegramMessage = await self._msg_queue.get()
                if isinstance(new_msg, TelegramMessage) and len(new_msg.text) > 0:
                    await self.send_msg_async(new_msg)
            except Exception as e:
                logger.error(str(e))
            await asyncio.sleep(0.1)

    async def send_msg_async(self, msg: TelegramMessage) -> None:
        config = self._chat_configs.get(msg.chat_label)
        if config is None:
            raise RuntimeError(f"Chat configuration for {msg.chat_label} not found.")
        reply_markup = self._reply_markup if self._listen_to_commands else None
        formatted_msg = f"\n{msg.text}\n"

        await self._bot.send_message(
            entity=config.chat_id,
            message=formatted_msg,
            reply_to=config.topic_id,
            parse_mode="html",
            buttons=reply_markup,
        )

    async def forward_message(
        self,
        chat_id: int,
        message_id: int,
        chat_label: str,
        reply_msg: str | None = None,
    ) -> None:
        config = self._chat_configs.get(chat_label)
        if config is None:
            raise RuntimeError(f"Chat configuration for {chat_label} not found.")

        request = functions.messages.ForwardMessagesRequest(
            from_peer=chat_id,
            id=[message_id],
            to_peer=config.chat_id,
            top_msg_id=config.topic_id,
        )
        update = await self._bot(request)
        message = self._bot._get_response_message(request, update, config.chat_id)
        message = message[0]

        if reply_msg is not None:
            await message.reply(reply_msg)

    async def retrieve_messages(
        self, chat_id: int, messages: list[str]
    ) -> NewMessage.Event:
        return await self._bot.get_messages(chat_id, ids=messages)

    # === Utilities ===

    @classmethod
    def get_text_from_update(
        cls, event: NewMessage.Event | Message, include_html: bool = False
    ) -> str | None:
        if isinstance(event, NewMessage.Event):
            message = event.message
        elif isinstance(event, Message):
            message = event
        else:
            raise ValueError("Unknown event type")
        result: str | None = message.text if include_html else message.raw_text
        return result

    @classmethod
    def get_date_from_update(
        cls, event: NewMessage.Event | Message, include_forward: bool = True
    ) -> datetime:
        source = event
        if include_forward and event.forward is not None:
            source = event.forward
        date: datetime = source.date
        return date

    @classmethod
    async def get_chat_title_from_update(
        cls, event: NewMessage.Event | Message, include_forward: bool = True
    ) -> str | None:
        source = event
        if include_forward and event.forward is not None:
            source = event.forward
        chat = await source.get_chat()
        return chat.title if chat is not None else None

    @classmethod
    async def get_sender_id_from_update(
        cls, event: NewMessage.Event | Message, include_forward: bool = True
    ) -> str:
        source = event
        if include_forward and event.forward is not None:
            source = event.forward
        sender_id: str = source.sender_id
        return sender_id

    @classmethod
    async def get_sender_name_from_update(
        cls, event: NewMessage.Event | Message, include_forward: bool = True
    ) -> str | None:
        source = event
        if include_forward and event.forward is not None:
            source = event.forward
        sender = await source.get_sender()
        return sender.username if sender is not None else None
