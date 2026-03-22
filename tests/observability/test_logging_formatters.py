"""Tests for log formatters: Text, Color, and JSON."""

from __future__ import annotations

import json
import logging

from processpype.observability.logging.formatters import (
    ColorFormatter,
    JsonFormatter,
    TextFormatter,
)


def _make_record(
    msg: str = "hello",
    level: int = logging.INFO,
    name: str = "test",
    **extra: object,
) -> logging.LogRecord:
    record = logging.LogRecord(name, level, "test.py", 10, msg, (), None)
    for k, v in extra.items():
        setattr(record, k, v)
    return record


class TestTextFormatter:
    def test_default_format(self):
        fmt = TextFormatter()
        record = _make_record()
        output = fmt.format(record)
        assert "hello" in output
        assert "INFO" in output

    def test_custom_format(self):
        fmt = TextFormatter(fmt="%(message)s - %(levelname)s")
        record = _make_record()
        output = fmt.format(record)
        assert output == "hello - INFO"


class TestColorFormatter:
    def test_info_has_color_codes(self):
        fmt = ColorFormatter()
        record = _make_record(level=logging.INFO)
        output = fmt.format(record)
        assert "\x1b[" in output
        assert "\x1b[0m" in output
        assert "hello" in output

    def test_warning_has_color(self):
        fmt = ColorFormatter()
        record = _make_record(level=logging.WARNING)
        output = fmt.format(record)
        assert "\x1b[" in output

    def test_error_has_color(self):
        fmt = ColorFormatter()
        record = _make_record(level=logging.ERROR)
        output = fmt.format(record)
        assert "\x1b[31" in output

    def test_critical_has_color(self):
        fmt = ColorFormatter()
        record = _make_record(level=logging.CRITICAL)
        output = fmt.format(record)
        assert "\x1b[31;1m" in output

    def test_debug_has_color(self):
        fmt = ColorFormatter()
        record = _make_record(level=logging.DEBUG)
        output = fmt.format(record)
        assert "\x1b[" in output

    def test_unknown_level_no_color(self):
        fmt = ColorFormatter()
        record = _make_record(level=99)
        output = fmt.format(record)
        # No color prefix for unknown levels, just the message
        assert "hello" in output


class TestJsonFormatter:
    def test_basic_json_output(self):
        fmt = JsonFormatter()
        record = _make_record()
        output = fmt.format(record)
        data = json.loads(output)
        assert data["message"] == "hello"
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert "timestamp" in data

    def test_includes_context_fields(self):
        fmt = JsonFormatter()
        record = _make_record(strategy_code="strat1", run_id="r1")
        output = fmt.format(record)
        data = json.loads(output)
        assert data["strategy_code"] == "strat1"
        assert data["run_id"] == "r1"

    def test_includes_extra_fields(self):
        fmt = JsonFormatter()
        record = _make_record(custom_field="custom_value")
        output = fmt.format(record)
        data = json.loads(output)
        assert data["custom_field"] == "custom_value"

    def test_includes_exception_info(self):
        fmt = JsonFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = _make_record()
            record.exc_info = sys.exc_info()
            output = fmt.format(record)
            data = json.loads(output)
            assert "exc_info" in data
            assert "ValueError" in data["exc_info"]

    def test_includes_stack_info(self):
        fmt = JsonFormatter()
        record = _make_record()
        record.stack_info = "Stack trace here"
        output = fmt.format(record)
        data = json.loads(output)
        assert data["stack_info"] == "Stack trace here"

    def test_excludes_reserved_attrs_from_extra(self):
        fmt = JsonFormatter()
        record = _make_record()
        output = fmt.format(record)
        data = json.loads(output)
        # Reserved attrs like "args", "exc_info" should not appear as extra
        assert "args" not in data
        assert "exc_text" not in data
