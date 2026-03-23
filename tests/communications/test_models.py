"""Tests for communication data models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from processpype.communications.models import (
    IncomingMessage,
    MessageSeverity,
    OutgoingMessage,
)


class TestMessageSeverity:
    """Tests for the MessageSeverity enum."""

    def test_values(self) -> None:
        assert MessageSeverity.DEBUG == "debug"
        assert MessageSeverity.INFO == "info"
        assert MessageSeverity.WARNING == "warning"
        assert MessageSeverity.ERROR == "error"
        assert MessageSeverity.CRITICAL == "critical"

    def test_is_str_enum(self) -> None:
        assert isinstance(MessageSeverity.INFO, str)


class TestOutgoingMessage:
    """Tests for the OutgoingMessage model."""

    def test_minimal(self) -> None:
        msg = OutgoingMessage(message="hello")
        assert msg.message == "hello"
        assert msg.label == "default"
        assert msg.source is None
        assert msg.severity == MessageSeverity.INFO
        assert msg.metadata == {}
        assert msg.subject is None

    def test_full(self) -> None:
        msg = OutgoingMessage(
            message="alert",
            label="alerts",
            source="service-1",
            severity=MessageSeverity.ERROR,
            metadata={"key": "val"},
            subject="Subject line",
        )
        assert msg.message == "alert"
        assert msg.label == "alerts"
        assert msg.source == "service-1"
        assert msg.severity == MessageSeverity.ERROR
        assert msg.metadata == {"key": "val"}
        assert msg.subject == "Subject line"

    def test_label_must_not_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            OutgoingMessage(message="x", label="")


class TestIncomingMessage:
    """Tests for the IncomingMessage model."""

    def test_minimal(self) -> None:
        msg = IncomingMessage(text="hi")
        assert msg.text == "hi"
        assert msg.sender is None
        assert msg.sender_id is None
        assert msg.chat_label == "default"
        assert msg.backend_name == ""
        assert msg.timestamp is None
        assert msg.metadata == {}
        assert msg.raw_event is None

    def test_full(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        raw = {"original": True}
        msg = IncomingMessage(
            text="command",
            sender="alice",
            sender_id="123",
            chat_label="ops",
            backend_name="telegram",
            timestamp=now,
            metadata={"foo": "bar"},
            raw_event=raw,
        )
        assert msg.text == "command"
        assert msg.sender == "alice"
        assert msg.sender_id == "123"
        assert msg.chat_label == "ops"
        assert msg.backend_name == "telegram"
        assert msg.timestamp == now
        assert msg.metadata == {"foo": "bar"}
        assert msg.raw_event == raw

    def test_raw_event_excluded_from_serialization(self) -> None:
        msg = IncomingMessage(text="hi", raw_event={"secret": True})
        data = msg.model_dump()
        assert "raw_event" not in data
