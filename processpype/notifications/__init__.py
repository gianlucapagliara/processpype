"""Notification subsystem for ProcessPype."""

from processpype.notifications.base import NotifierBase
from processpype.notifications.dispatcher import (
    NotificationHandler,
    clear_notification_handler,
    emit_notification,
    set_notification_handler,
)
from processpype.notifications.email import EmailBot
from processpype.notifications.models import NotificationIntent

__all__ = [
    "EmailBot",
    "NotificationHandler",
    "NotificationIntent",
    "NotifierBase",
    "clear_notification_handler",
    "emit_notification",
    "set_notification_handler",
]
