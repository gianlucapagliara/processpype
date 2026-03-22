"""Base notifier abstract class."""

from abc import ABC, abstractmethod
from typing import Any


class NotifierBase(ABC):
    """Base class for notification channel implementations."""

    def __init__(self) -> None:
        self._started = False

    @abstractmethod
    def add_msg_to_queue(
        self, msg: str, label: str = "default", **kwargs: Any
    ) -> None: ...

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...
