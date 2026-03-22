"""Notification dispatcher — handler registration and emit pattern."""

import logging
from collections.abc import Callable

from processpype.notifications.models import NotificationIntent

_logger = logging.getLogger(__name__)

NotificationHandler = Callable[[NotificationIntent], None]
_notification_handler: NotificationHandler | None = None


def set_notification_handler(handler: NotificationHandler | None) -> None:
    global _notification_handler
    _notification_handler = handler


def clear_notification_handler() -> None:
    set_notification_handler(None)


def emit_notification(intent: NotificationIntent) -> None:
    if _notification_handler is None:
        _logger.info(
            "Notification without runtime handler: source=%s label=%s message=%s",
            intent.source,
            intent.label,
            intent.message,
        )
        return

    try:
        _notification_handler(intent)
    except Exception:
        _logger.exception("Notification handler failed")
