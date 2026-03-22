"""Notification data models."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NotificationIntent:
    """A structured notification to be dispatched."""

    message: str
    label: str = "default"
    source: str | None = None
    severity: str = "info"
    metadata: dict[str, Any] = field(default_factory=dict)
