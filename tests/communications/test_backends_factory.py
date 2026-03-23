"""Tests for the backend factory and registry."""

from __future__ import annotations

from unittest.mock import patch

from processpype.communications.backends import (
    _backend_registry,
    create_communicator,
    register_backend,
)
from processpype.communications.base import NoOpCommunicator
from processpype.config.models import CommunicatorBackendConfig


class _DummyCommunicator(NoOpCommunicator):
    """A custom communicator for testing the registry."""

    def __init__(self, name: str, config: CommunicatorBackendConfig) -> None:
        super().__init__()
        self._name = name


class TestRegisterBackend:
    """Tests for register_backend."""

    def test_register_and_create(self) -> None:
        original = dict(_backend_registry)
        try:
            register_backend("custom", _DummyCommunicator)
            config = CommunicatorBackendConfig(type="custom")
            comm = create_communicator("my-custom", config)
            assert isinstance(comm, _DummyCommunicator)
            assert comm.name == "my-custom"
        finally:
            _backend_registry.clear()
            _backend_registry.update(original)


class TestCreateCommunicator:
    """Tests for create_communicator."""

    def test_unknown_type_returns_noop(self) -> None:
        config = CommunicatorBackendConfig(type="unknown_backend")
        comm = create_communicator("test", config)
        assert isinstance(comm, NoOpCommunicator)

    def test_telegram_import_error_returns_noop(self) -> None:
        config = CommunicatorBackendConfig(type="telegram")
        with patch.dict("sys.modules", {"telethon": None}):
            comm = create_communicator("tg", config)
            assert isinstance(comm, NoOpCommunicator)

    def test_email_import_error_returns_noop(self) -> None:
        config = CommunicatorBackendConfig(type="email")
        with patch.dict("sys.modules", {"aiosmtplib": None}):
            comm = create_communicator("mail", config)
            assert isinstance(comm, NoOpCommunicator)

    def test_plugin_registry_takes_priority(self) -> None:
        original = dict(_backend_registry)
        try:
            register_backend("telegram", _DummyCommunicator)
            config = CommunicatorBackendConfig(type="telegram")
            comm = create_communicator("tg", config)
            # Should use the registered factory, not the built-in
            assert isinstance(comm, _DummyCommunicator)
        finally:
            _backend_registry.clear()
            _backend_registry.update(original)
