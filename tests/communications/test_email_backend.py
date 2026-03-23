"""Tests for the Email communicator backend.

Since aiosmtplib is an optional dependency, we mock it at the sys.modules level
before importing the EmailCommunicator.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from processpype.communications.models import MessageSeverity, OutgoingMessage

# --- Module-level mocking setup ---


def _create_mock_aiosmtplib() -> ModuleType:
    """Create a mock aiosmtplib module."""
    mock_mod = ModuleType("aiosmtplib")
    mock_mod.SMTP = MagicMock  # type: ignore[attr-defined]
    mock_mod.SMTPServerDisconnected = type(  # type: ignore[attr-defined]
        "SMTPServerDisconnected", (Exception,), {}
    )
    return mock_mod


@pytest.fixture(autouse=True)
def _mock_aiosmtplib():
    """Ensure aiosmtplib is mocked for all tests in this module."""
    mock_mod = _create_mock_aiosmtplib()
    with patch.dict(sys.modules, {"aiosmtplib": mock_mod}):
        # Force re-import of the email module with the mock
        mod_key = "processpype.communications.backends.email"
        if mod_key in sys.modules:
            del sys.modules[mod_key]
        yield mock_mod
        if mod_key in sys.modules:
            del sys.modules[mod_key]


def _make_config() -> MagicMock:
    config = MagicMock()
    config.type = "email"
    config.enabled = True
    config.labels = ["default"]
    config.host = "smtp.example.com"
    config.port = 587
    config.username = "user"
    config.password = "pass"
    config.from_address = "noreply@example.com"
    config.use_tls = False
    config.start_tls = True
    config.default_recipients = ["admin@example.com"]
    return config


def _make_smtp_mock() -> AsyncMock:
    smtp = AsyncMock()
    smtp.connect = AsyncMock()
    smtp.starttls = AsyncMock()
    smtp.login = AsyncMock()
    smtp.quit = AsyncMock()
    smtp.send_message = AsyncMock()
    return smtp


class TestEmailCommunicatorStart:
    """Tests for EmailCommunicator start lifecycle."""

    async def test_start_connects_and_logs_in(
        self, _mock_aiosmtplib: ModuleType
    ) -> None:
        smtp = _make_smtp_mock()
        _mock_aiosmtplib.SMTP = MagicMock(return_value=smtp)  # type: ignore[attr-defined]
        from processpype.communications.backends.email import EmailCommunicator

        config = _make_config()
        comm = EmailCommunicator("test-email", config)
        await comm.start()

        smtp.connect.assert_awaited_once()
        smtp.starttls.assert_awaited_once()
        smtp.login.assert_awaited_once_with("user", "pass")
        assert comm.is_started is True

    async def test_start_skips_starttls_when_use_tls(
        self, _mock_aiosmtplib: ModuleType
    ) -> None:
        smtp = _make_smtp_mock()
        _mock_aiosmtplib.SMTP = MagicMock(return_value=smtp)  # type: ignore[attr-defined]
        from processpype.communications.backends.email import EmailCommunicator

        config = _make_config()
        config.use_tls = True
        config.start_tls = True
        comm = EmailCommunicator("test-email", config)
        await comm.start()

        smtp.starttls.assert_not_awaited()

    async def test_start_skips_login_when_no_credentials(
        self, _mock_aiosmtplib: ModuleType
    ) -> None:
        smtp = _make_smtp_mock()
        _mock_aiosmtplib.SMTP = MagicMock(return_value=smtp)  # type: ignore[attr-defined]
        from processpype.communications.backends.email import EmailCommunicator

        config = _make_config()
        config.username = ""
        config.password = ""
        comm = EmailCommunicator("test-email", config)
        await comm.start()

        smtp.login.assert_not_awaited()

    async def test_start_is_idempotent(self, _mock_aiosmtplib: ModuleType) -> None:
        smtp = _make_smtp_mock()
        _mock_aiosmtplib.SMTP = MagicMock(return_value=smtp)  # type: ignore[attr-defined]
        from processpype.communications.backends.email import EmailCommunicator

        config = _make_config()
        comm = EmailCommunicator("test-email", config)
        await comm.start()
        await comm.start()

        smtp.connect.assert_awaited_once()


class TestEmailCommunicatorStop:
    """Tests for EmailCommunicator stop lifecycle."""

    async def test_stop(self, _mock_aiosmtplib: ModuleType) -> None:
        smtp = _make_smtp_mock()
        _mock_aiosmtplib.SMTP = MagicMock(return_value=smtp)  # type: ignore[attr-defined]
        from processpype.communications.backends.email import EmailCommunicator

        config = _make_config()
        comm = EmailCommunicator("test-email", config)
        await comm.start()
        await comm.stop()

        smtp.quit.assert_awaited_once()
        assert comm.is_started is False
        assert comm._smtp is None

    async def test_stop_handles_quit_failure(
        self, _mock_aiosmtplib: ModuleType
    ) -> None:
        smtp = _make_smtp_mock()
        smtp.quit.side_effect = RuntimeError("already closed")
        _mock_aiosmtplib.SMTP = MagicMock(return_value=smtp)  # type: ignore[attr-defined]
        from processpype.communications.backends.email import EmailCommunicator

        config = _make_config()
        comm = EmailCommunicator("test-email", config)
        await comm.start()
        await comm.stop()  # should not raise

        assert comm._smtp is None


class TestEmailCommunicatorSend:
    """Tests for EmailCommunicator send."""

    async def test_send_uses_default_recipients(
        self, _mock_aiosmtplib: ModuleType
    ) -> None:
        smtp = _make_smtp_mock()
        _mock_aiosmtplib.SMTP = MagicMock(return_value=smtp)  # type: ignore[attr-defined]
        from processpype.communications.backends.email import EmailCommunicator

        config = _make_config()
        comm = EmailCommunicator("test-email", config)
        await comm.start()

        msg = OutgoingMessage(message="Test body")
        await comm.send(msg)

        smtp.send_message.assert_awaited_once()
        sent = smtp.send_message.call_args[0][0]
        assert sent["To"] == "admin@example.com"
        assert sent["From"] == "noreply@example.com"

    async def test_send_uses_metadata_recipients(
        self, _mock_aiosmtplib: ModuleType
    ) -> None:
        smtp = _make_smtp_mock()
        _mock_aiosmtplib.SMTP = MagicMock(return_value=smtp)  # type: ignore[attr-defined]
        from processpype.communications.backends.email import EmailCommunicator

        config = _make_config()
        comm = EmailCommunicator("test-email", config)
        await comm.start()

        msg = OutgoingMessage(
            message="Test",
            metadata={"recipients": ["custom@example.com"]},
        )
        await comm.send(msg)

        sent = smtp.send_message.call_args[0][0]
        assert sent["To"] == "custom@example.com"

    async def test_send_with_custom_subject(self, _mock_aiosmtplib: ModuleType) -> None:
        smtp = _make_smtp_mock()
        _mock_aiosmtplib.SMTP = MagicMock(return_value=smtp)  # type: ignore[attr-defined]
        from processpype.communications.backends.email import EmailCommunicator

        config = _make_config()
        comm = EmailCommunicator("test-email", config)
        await comm.start()

        msg = OutgoingMessage(message="body", subject="Custom Subject")
        await comm.send(msg)

        sent = smtp.send_message.call_args[0][0]
        assert sent["Subject"] == "Custom Subject"

    async def test_send_default_subject_includes_severity(
        self, _mock_aiosmtplib: ModuleType
    ) -> None:
        smtp = _make_smtp_mock()
        _mock_aiosmtplib.SMTP = MagicMock(return_value=smtp)  # type: ignore[attr-defined]
        from processpype.communications.backends.email import EmailCommunicator

        config = _make_config()
        comm = EmailCommunicator("test-email", config)
        await comm.start()

        msg = OutgoingMessage(message="body", severity=MessageSeverity.ERROR)
        await comm.send(msg)

        sent = smtp.send_message.call_args[0][0]
        assert sent["Subject"] == "[ERROR] Notification"

    async def test_send_no_recipients_skips(self, _mock_aiosmtplib: ModuleType) -> None:
        smtp = _make_smtp_mock()
        _mock_aiosmtplib.SMTP = MagicMock(return_value=smtp)  # type: ignore[attr-defined]
        from processpype.communications.backends.email import EmailCommunicator

        config = _make_config()
        config.default_recipients = []
        comm = EmailCommunicator("test-email", config)
        await comm.start()

        msg = OutgoingMessage(message="body")
        await comm.send(msg)

        smtp.send_message.assert_not_awaited()

    async def test_send_not_started_skips(self, _mock_aiosmtplib: ModuleType) -> None:
        _mock_aiosmtplib.SMTP = MagicMock(return_value=_make_smtp_mock())  # type: ignore[attr-defined]
        from processpype.communications.backends.email import EmailCommunicator

        config = _make_config()
        comm = EmailCommunicator("test-email", config)
        msg = OutgoingMessage(message="body")
        await comm.send(msg)  # should not raise

    async def test_send_reconnects_on_disconnect(
        self, _mock_aiosmtplib: ModuleType
    ) -> None:
        smtp = _make_smtp_mock()
        _mock_aiosmtplib.SMTP = MagicMock(return_value=smtp)  # type: ignore[attr-defined]
        SMTPDisconnected = _mock_aiosmtplib.SMTPServerDisconnected  # type: ignore[attr-defined]

        call_count = 0

        async def send_side_effect(*args: object, **kwargs: object) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise SMTPDisconnected("gone")

        smtp.send_message.side_effect = send_side_effect

        from processpype.communications.backends.email import EmailCommunicator

        config = _make_config()
        comm = EmailCommunicator("test-email", config)
        await comm.start()

        msg = OutgoingMessage(message="retry test")
        await comm.send(msg)

        assert smtp.send_message.await_count == 2

    async def test_send_reconnect_failure_is_caught(
        self, _mock_aiosmtplib: ModuleType
    ) -> None:
        smtp = _make_smtp_mock()
        SMTPDisconnected = _mock_aiosmtplib.SMTPServerDisconnected  # type: ignore[attr-defined]
        smtp.send_message.side_effect = SMTPDisconnected("gone")

        connect_count = 0

        async def connect_side_effect() -> None:
            nonlocal connect_count
            connect_count += 1
            if connect_count > 1:
                raise ConnectionError("reconnect failed")

        smtp.connect.side_effect = connect_side_effect
        _mock_aiosmtplib.SMTP = MagicMock(return_value=smtp)  # type: ignore[attr-defined]

        from processpype.communications.backends.email import EmailCommunicator

        config = _make_config()
        comm = EmailCommunicator("test-email", config)
        await comm.start()

        msg = OutgoingMessage(message="will fail")
        # Should not raise — error is caught and logged, message is dropped
        await comm.send(msg)
