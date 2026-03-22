"""Telegram notification channel.

Requires the ``telegram`` optional extra: ``pip install processpype[telegram]``
"""

try:
    from processpype.notifications.telegram.bot import (
        ChatConfiguration,
        TelegramBot,
        TelegramMessage,
        authorized_only,
    )

    __all__ = [
        "ChatConfiguration",
        "TelegramBot",
        "TelegramMessage",
        "authorized_only",
    ]
except ImportError:
    __all__ = []
