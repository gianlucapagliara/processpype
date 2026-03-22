"""Base notifier abstract class."""

from typing import Any


class NotifierBase:
    """Base class for notification channel implementations."""

    def __init__(self) -> None:
        self._started = False

    def add_msg_to_queue(self, msg: str, label: str = "default", **kwargs: Any) -> None:
        raise NotImplementedError

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError
