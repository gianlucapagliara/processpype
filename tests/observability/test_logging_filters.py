"""Tests for logging filters."""

import logging

from processpype.observability.logging.filters import ContextFilter, RedactionFilter


class TestContextFilter:
    def test_injects_static_context(self):
        f = ContextFilter(static_context={"app": "myapp"})
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        result = f.filter(record)
        assert result is True
        assert record.app == "myapp"

    def test_does_not_overwrite_existing_attribute(self):
        f = ContextFilter(static_context={"levelno": 99})
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        result = f.filter(record)
        assert result is True
        assert record.levelno == logging.INFO  # not overwritten

    def test_injects_dynamic_context(self):
        from processpype.observability.logging.context import (
            clear_log_context,
            set_log_context,
        )

        set_log_context(request_id="abc123")
        try:
            f = ContextFilter()
            record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
            f.filter(record)
            assert record.request_id == "abc123"
        finally:
            clear_log_context()

    def test_merges_static_and_dynamic(self):
        from processpype.observability.logging.context import (
            clear_log_context,
            set_log_context,
        )

        set_log_context(dynamic_key="dyn")
        try:
            f = ContextFilter(static_context={"static_key": "stat"})
            record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
            f.filter(record)
            assert record.static_key == "stat"
            assert record.dynamic_key == "dyn"
        finally:
            clear_log_context()

    def test_skips_none_values_from_context(self):
        f = ContextFilter(static_context={"k": None})
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        f.filter(record)
        assert not hasattr(record, "k")


class TestRedactionFilter:
    def test_redacts_password_in_message(self):
        f = RedactionFilter()
        record = logging.LogRecord(
            "test", logging.INFO, "", 0, "password=secret123", (), None
        )
        f.filter(record)
        assert "secret123" not in record.msg
        assert "***" in record.msg

    def test_redacts_api_key_in_message(self):
        f = RedactionFilter()
        record = logging.LogRecord(
            "test", logging.INFO, "", 0, "api_key=mykey123", (), None
        )
        f.filter(record)
        assert "mykey123" not in record.msg

    def test_redacts_token_in_message(self):
        f = RedactionFilter()
        record = logging.LogRecord(
            "test", logging.INFO, "", 0, "token=tok123", (), None
        )
        f.filter(record)
        assert "tok123" not in record.msg

    def test_custom_patterns(self):
        f = RedactionFilter(patterns=[r"(ssn)\s*[:=]\s*(\S+)"])
        record = logging.LogRecord(
            "test", logging.INFO, "", 0, "ssn=123-45-6789", (), None
        )
        f.filter(record)
        assert "123-45-6789" not in record.msg

    def test_custom_replacement(self):
        f = RedactionFilter(replacement="[REDACTED]")
        record = logging.LogRecord(
            "test", logging.INFO, "", 0, "password=secret", (), None
        )
        f.filter(record)
        assert "[REDACTED]" in record.msg

    def test_redacts_in_args_tuple(self):
        f = RedactionFilter()
        record = logging.LogRecord(
            "test", logging.INFO, "", 0, "data: %s", ("password=secret",), None
        )
        f.filter(record)
        assert "secret" not in record.args[0]

    def test_redacts_in_args_dict(self):
        f = RedactionFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "data", (), None)
        record.args = {"key": "token=abc123"}
        f.filter(record)
        assert "abc123" not in record.args["key"]

    def test_redacts_nested_list_in_args(self):
        f = RedactionFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        record.args = ["password=secret"]
        f.filter(record)
        assert "secret" not in record.args[0]

    def test_redacts_extra_attribute(self):
        f = RedactionFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        record.extra = {"data": "api_key=xyz"}
        f.filter(record)
        assert "xyz" not in record.extra["data"]

    def test_redacts_tuple_values(self):
        f = RedactionFilter()
        result = f._redact_value(("password=secret",))
        assert isinstance(result, tuple)
        assert "secret" not in result[0]

    def test_redacts_set_values(self):
        f = RedactionFilter()
        result = f._redact_value({"password=secret"})
        assert isinstance(result, set)

    def test_non_string_passthrough(self):
        f = RedactionFilter()
        assert f._redact_value(42) == 42
        assert f._redact_value(None) is None

    def test_no_args_no_error(self):
        f = RedactionFilter()
        record = logging.LogRecord(
            "test", logging.INFO, "", 0, "clean message", (), None
        )
        record.args = None
        f.filter(record)
        assert record.msg == "clean message"

    def test_non_string_msg(self):
        f = RedactionFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, 42, (), None)
        f.filter(record)
        assert record.msg == 42
