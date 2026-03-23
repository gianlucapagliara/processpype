"""Tests for the Telegram communicator backend.

Since telethon is an optional dependency, we mock it at the sys.modules level
before importing the TelegramCommunicator.
"""

from __future__ import annotations

import sys
from datetime import datetime
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from processpype.communications.models import IncomingMessage, OutgoingMessage

# --- Module-level mocking setup ---


def _create_mock_telethon() -> dict[str, ModuleType]:
    """Create mock telethon modules."""
    telethon = ModuleType("telethon")
    telethon.TelegramClient = MagicMock  # type: ignore[attr-defined]

    events = ModuleType("telethon.events")
    events.NewMessage = MagicMock()  # type: ignore[attr-defined]

    sessions = ModuleType("telethon.sessions")
    sessions.StringSession = MagicMock  # type: ignore[attr-defined]

    tl = ModuleType("telethon.tl")
    tl_custom = ModuleType("telethon.tl.custom")
    tl_custom.Message = MagicMock  # type: ignore[attr-defined]

    telethon.events = events  # type: ignore[attr-defined]
    telethon.sessions = sessions  # type: ignore[attr-defined]
    telethon.tl = tl  # type: ignore[attr-defined]

    return {
        "telethon": telethon,
        "telethon.events": events,
        "telethon.sessions": sessions,
        "telethon.tl": tl,
        "telethon.tl.custom": tl_custom,
    }


@pytest.fixture(autouse=True)
def _mock_telethon():
    """Ensure telethon is mocked for all tests in this module."""
    mocks = _create_mock_telethon()
    with patch.dict(sys.modules, mocks):
        mod_key = "processpype.communications.backends.telegram"
        if mod_key in sys.modules:
            del sys.modules[mod_key]
        yield mocks
        if mod_key in sys.modules:
            del sys.modules[mod_key]


def _make_config(
    *,
    listen: bool = False,
    chats: dict | None = None,
) -> MagicMock:
    """Create a mock TelegramCommunicatorConfig."""
    config = MagicMock()
    config.type = "telegram"
    config.enabled = True
    config.labels = ["default"]
    config.api_id = 12345
    config.api_hash = "abc123"
    config.token = "bot:token"
    config.session_string = "test-session"
    config.listen_to_commands = listen

    if chats is None:
        default_chat = MagicMock()
        default_chat.chat_id = "100"
        default_chat.topic_id = None
        default_chat.command_authorized = True
        default_chat.active = True
        chats = {"default": default_chat}

    config.chats = chats
    return config


def _make_mock_client() -> AsyncMock:
    """Create a mock TelegramClient."""
    client = AsyncMock()
    client.start = AsyncMock()
    client.disconnect = AsyncMock()
    client.is_connected = MagicMock(return_value=True)
    client.send_message = AsyncMock()
    client.add_event_handler = MagicMock()
    client.run_until_disconnected = AsyncMock()
    return client


class TestDivideChunks:
    """Tests for _divide_chunks helper."""

    def test_divide_chunks(self) -> None:
        from processpype.communications.backends.telegram import _divide_chunks

        result = _divide_chunks([1, 2, 3, 4, 5], n=2)
        assert result == [[1, 2], [3, 4], [5]]

    def test_divide_chunks_empty(self) -> None:
        from processpype.communications.backends.telegram import _divide_chunks

        result = _divide_chunks([], n=5)
        assert result == []

    def test_divide_chunks_exact(self) -> None:
        from processpype.communications.backends.telegram import _divide_chunks

        result = _divide_chunks([1, 2, 3, 4], n=2)
        assert result == [[1, 2], [3, 4]]


class TestTelegramCommunicatorLifecycle:
    """Tests for start/stop lifecycle."""

    async def test_start_connects_client(self, _mock_telethon: dict) -> None:
        mock_client = _make_mock_client()
        _mock_telethon["telethon"].TelegramClient = MagicMock(return_value=mock_client)

        from processpype.communications.backends.telegram import TelegramCommunicator

        config = _make_config()
        comm = TelegramCommunicator("tg", config)
        await comm.start()

        mock_client.start.assert_awaited_once()
        assert comm.is_started is True
        await comm.stop()

    async def test_start_is_idempotent(self, _mock_telethon: dict) -> None:
        mock_client = _make_mock_client()
        _mock_telethon["telethon"].TelegramClient = MagicMock(return_value=mock_client)

        from processpype.communications.backends.telegram import TelegramCommunicator

        config = _make_config()
        comm = TelegramCommunicator("tg", config)
        await comm.start()
        await comm.start()

        mock_client.start.assert_awaited_once()
        await comm.stop()

    async def test_stop_cancels_tasks_and_disconnects(
        self, _mock_telethon: dict
    ) -> None:
        mock_client = _make_mock_client()
        _mock_telethon["telethon"].TelegramClient = MagicMock(return_value=mock_client)

        from processpype.communications.backends.telegram import TelegramCommunicator

        config = _make_config()
        comm = TelegramCommunicator("tg", config)
        await comm.start()

        assert comm._drain_task is not None
        await comm.stop()

        assert comm._drain_task is None
        assert comm._bot is None
        assert comm.is_started is False
        mock_client.disconnect.assert_awaited_once()

    async def test_supports_receiving(self, _mock_telethon: dict) -> None:
        _mock_telethon["telethon"].TelegramClient = MagicMock(
            return_value=_make_mock_client()
        )

        from processpype.communications.backends.telegram import TelegramCommunicator

        assert (
            TelegramCommunicator("a", _make_config(listen=True)).supports_receiving
            is True
        )
        assert (
            TelegramCommunicator("b", _make_config(listen=False)).supports_receiving
            is False
        )


class TestTelegramSend:
    """Tests for message sending."""

    async def test_send_queues_message(self, _mock_telethon: dict) -> None:
        _mock_telethon["telethon"].TelegramClient = MagicMock(
            return_value=_make_mock_client()
        )
        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config())
        msg = OutgoingMessage(message="hello", label="default")
        await comm.send(msg)

        assert comm._msg_queue.qsize() == 1
        text, label = comm._msg_queue.get_nowait()
        assert text == "hello"
        assert label == "default"

    async def test_send_chunks_long_messages(self, _mock_telethon: dict) -> None:
        _mock_telethon["telethon"].TelegramClient = MagicMock(
            return_value=_make_mock_client()
        )
        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config())
        lines = [f"line {i}" for i in range(60)]
        msg = OutgoingMessage(message="\n".join(lines), label="default")
        await comm.send(msg)

        assert comm._msg_queue.qsize() == 2

    async def test_send_to_chat_with_label(self, _mock_telethon: dict) -> None:
        mock_client = _make_mock_client()
        _mock_telethon["telethon"].TelegramClient = MagicMock(return_value=mock_client)
        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config())
        comm._bot = mock_client
        comm._started = True

        await comm._send_to_chat("hello", "default")

        mock_client.send_message.assert_awaited_once()
        kw = mock_client.send_message.call_args[1]
        assert kw["entity"] == "100"
        assert "hello" in kw["message"]

    async def test_send_to_chat_unknown_label_falls_back_to_default(
        self, _mock_telethon: dict
    ) -> None:
        mock_client = _make_mock_client()
        _mock_telethon["telethon"].TelegramClient = MagicMock(return_value=mock_client)
        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config())
        comm._bot = mock_client

        await comm._send_to_chat("hello", "nonexistent")
        mock_client.send_message.assert_awaited_once()

    async def test_send_to_chat_inactive_skips(self, _mock_telethon: dict) -> None:
        mock_client = _make_mock_client()
        _mock_telethon["telethon"].TelegramClient = MagicMock(return_value=mock_client)

        chat = MagicMock()
        chat.chat_id = "100"
        chat.topic_id = None
        chat.active = False
        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config(chats={"default": chat}))
        comm._bot = mock_client

        await comm._send_to_chat("hello", "default")
        mock_client.send_message.assert_not_awaited()

    async def test_send_to_chat_no_config_no_default(
        self, _mock_telethon: dict
    ) -> None:
        mock_client = _make_mock_client()
        _mock_telethon["telethon"].TelegramClient = MagicMock(return_value=mock_client)
        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config(chats={}))
        comm._bot = mock_client

        await comm._send_to_chat("hello", "unknown")
        mock_client.send_message.assert_not_awaited()

    async def test_send_to_chat_no_bot(self, _mock_telethon: dict) -> None:
        _mock_telethon["telethon"].TelegramClient = MagicMock(
            return_value=_make_mock_client()
        )
        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config())
        comm._bot = None

        await comm._send_to_chat("hello", "default")  # should not raise

    async def test_send_drops_when_queue_full(self, _mock_telethon: dict) -> None:
        _mock_telethon["telethon"].TelegramClient = MagicMock(
            return_value=_make_mock_client()
        )
        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config())
        # Fill the queue to capacity
        for i in range(comm.MAX_QUEUE_SIZE):
            comm._msg_queue.put_nowait((f"msg-{i}", "default"))

        # This should not raise, just log a warning and drop
        msg = OutgoingMessage(message="overflow", label="default")
        await comm.send(msg)

        assert comm._msg_queue.qsize() == comm.MAX_QUEUE_SIZE


class TestTelegramRetry:
    """Tests for retry and reconnection logic."""

    async def test_send_with_retry_succeeds_after_failure(
        self, _mock_telethon: dict
    ) -> None:
        mock_client = _make_mock_client()
        _mock_telethon["telethon"].TelegramClient = MagicMock(return_value=mock_client)

        call_count = 0

        async def send_side_effect(**kwargs: object) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("temp failure")

        mock_client.send_message.side_effect = send_side_effect

        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config())
        comm._bot = mock_client
        comm._started = True

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await comm._send_with_retry("hello", "default", max_retries=3)

        assert call_count == 2

    async def test_send_with_retry_drops_after_max(self, _mock_telethon: dict) -> None:
        mock_client = _make_mock_client()
        mock_client.send_message.side_effect = RuntimeError("permanent failure")
        _mock_telethon["telethon"].TelegramClient = MagicMock(return_value=mock_client)

        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config())
        comm._bot = mock_client
        comm._started = True

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await comm._send_with_retry("hello", "default", max_retries=2)

        assert mock_client.send_message.await_count == 2

    async def test_ensure_connected_reconnects(self, _mock_telethon: dict) -> None:
        mock_client = _make_mock_client()
        mock_client.is_connected = MagicMock(return_value=False)
        _mock_telethon["telethon"].TelegramClient = MagicMock(return_value=mock_client)

        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config())
        comm._bot = mock_client
        await comm._ensure_connected()

        mock_client.connect.assert_awaited_once()

    async def test_ensure_connected_raises_on_failure(
        self, _mock_telethon: dict
    ) -> None:
        mock_client = _make_mock_client()
        mock_client.is_connected = MagicMock(return_value=False)
        mock_client.connect.side_effect = ConnectionError("cannot connect")
        _mock_telethon["telethon"].TelegramClient = MagicMock(return_value=mock_client)

        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config())
        comm._bot = mock_client

        with pytest.raises(ConnectionError):
            await comm._ensure_connected()


class TestTelegramAuthorization:
    """Tests for _is_authorized."""

    def _make_event(
        self, chat_id: str = "100", topic_id: int | None = None
    ) -> MagicMock:
        event = MagicMock()
        event.chat_id = int(chat_id)
        event.message.reply_to = None
        if topic_id is not None:
            event.message.reply_to = MagicMock()
            event.message.reply_to.reply_to_msg_id = topic_id
        return event

    def test_authorized_chat(self, _mock_telethon: dict) -> None:
        _mock_telethon["telethon"].TelegramClient = MagicMock(
            return_value=_make_mock_client()
        )
        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config())
        assert comm._is_authorized(self._make_event("100")) is True

    def test_unauthorized_chat(self, _mock_telethon: dict) -> None:
        _mock_telethon["telethon"].TelegramClient = MagicMock(
            return_value=_make_mock_client()
        )
        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config())
        assert comm._is_authorized(self._make_event("999")) is False

    def test_authorized_with_topic(self, _mock_telethon: dict) -> None:
        _mock_telethon["telethon"].TelegramClient = MagicMock(
            return_value=_make_mock_client()
        )
        chat = MagicMock()
        chat.chat_id = "100"
        chat.topic_id = 42
        chat.command_authorized = True
        chat.active = True

        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config(chats={"default": chat}))
        assert comm._is_authorized(self._make_event("100", topic_id=42)) is True

    def test_wrong_topic_unauthorized(self, _mock_telethon: dict) -> None:
        _mock_telethon["telethon"].TelegramClient = MagicMock(
            return_value=_make_mock_client()
        )
        chat = MagicMock()
        chat.chat_id = "100"
        chat.topic_id = 42
        chat.command_authorized = True
        chat.active = True

        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config(chats={"default": chat}))
        assert comm._is_authorized(self._make_event("100", topic_id=99)) is False

    def test_not_command_authorized(self, _mock_telethon: dict) -> None:
        _mock_telethon["telethon"].TelegramClient = MagicMock(
            return_value=_make_mock_client()
        )
        chat = MagicMock()
        chat.chat_id = "100"
        chat.topic_id = None
        chat.command_authorized = False
        chat.active = True

        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config(chats={"default": chat}))
        assert comm._is_authorized(self._make_event("100")) is False


class TestTelegramChatLabelResolution:
    """Tests for _resolve_chat_label."""

    def test_resolves_matching_label(self, _mock_telethon: dict) -> None:
        _mock_telethon["telethon"].TelegramClient = MagicMock(
            return_value=_make_mock_client()
        )
        chat = MagicMock()
        chat.chat_id = "100"
        chat.topic_id = None

        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config(chats={"alerts": chat}))

        event = MagicMock()
        event.chat_id = 100
        event.message.reply_to = None
        assert comm._resolve_chat_label(event) == "alerts"

    def test_returns_default_for_unknown(self, _mock_telethon: dict) -> None:
        _mock_telethon["telethon"].TelegramClient = MagicMock(
            return_value=_make_mock_client()
        )
        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config())

        event = MagicMock()
        event.chat_id = 999
        event.message.reply_to = None
        assert comm._resolve_chat_label(event) == "default"


class TestTelegramIncoming:
    """Tests for _on_new_message."""

    async def test_incoming_message_published(self, _mock_telethon: dict) -> None:
        _mock_telethon["telethon"].TelegramClient = MagicMock(
            return_value=_make_mock_client()
        )
        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config(listen=True))
        received: list[IncomingMessage] = []
        comm.set_incoming_handler(lambda msg: received.append(msg))

        event = MagicMock()
        event.chat_id = 100
        event.message.raw_text = "hello"
        event.sender_id = 42
        event.message.reply_to = None
        event.get_sender = AsyncMock(return_value=MagicMock(username="alice"))
        # No forward attribute
        del event.forward
        event.date = datetime(2026, 1, 1)

        await comm._on_new_message(event)

        assert len(received) == 1
        assert received[0].text == "hello"
        assert received[0].sender == "alice"

    async def test_incoming_unauthorized_rejected(self, _mock_telethon: dict) -> None:
        _mock_telethon["telethon"].TelegramClient = MagicMock(
            return_value=_make_mock_client()
        )
        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config())
        received: list[IncomingMessage] = []
        comm.set_incoming_handler(lambda msg: received.append(msg))

        event = MagicMock()
        event.chat_id = 999
        event.message.reply_to = None

        await comm._on_new_message(event)
        assert len(received) == 0

    async def test_incoming_no_handler_does_nothing(self, _mock_telethon: dict) -> None:
        _mock_telethon["telethon"].TelegramClient = MagicMock(
            return_value=_make_mock_client()
        )
        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config())

        event = MagicMock()
        event.chat_id = 100
        event.message.reply_to = None

        await comm._on_new_message(event)  # should not raise

    async def test_incoming_handler_exception_is_caught(
        self, _mock_telethon: dict
    ) -> None:
        _mock_telethon["telethon"].TelegramClient = MagicMock(
            return_value=_make_mock_client()
        )
        from processpype.communications.backends.telegram import TelegramCommunicator

        comm = TelegramCommunicator("tg", _make_config(listen=True))

        def bad_handler(msg: IncomingMessage) -> None:
            raise ValueError("handler error")

        comm.set_incoming_handler(bad_handler)

        event = MagicMock()
        event.chat_id = 100
        event.message.raw_text = "hello"
        event.sender_id = 42
        event.message.reply_to = None
        event.get_sender = AsyncMock(return_value=MagicMock(username="bob"))
        del event.forward
        event.date = datetime(2026, 1, 1)

        await comm._on_new_message(event)  # should not raise
