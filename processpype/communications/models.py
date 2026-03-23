"""Communication data models."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MessageSeverity(StrEnum):
    """Severity level for outgoing messages."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class OutgoingMessage(BaseModel):
    """A message to send via a communicator backend."""

    message: str
    label: str = Field(default="default", min_length=1)
    source: str | None = None
    severity: MessageSeverity = MessageSeverity.INFO
    metadata: dict[str, Any] = Field(default_factory=dict)
    subject: str | None = None


class IncomingMessage(BaseModel):
    """A message received from a communicator backend (published as event)."""

    text: str
    sender: str | None = None
    sender_id: str | None = None
    chat_label: str = "default"
    backend_name: str = ""
    timestamp: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_event: Any = Field(default=None, exclude=True)


MessageHandler = Callable[[IncomingMessage], Awaitable[None]]
