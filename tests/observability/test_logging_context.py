"""Tests for logging context (ContextVar-based)."""

from processpype.observability.logging.context import (
    clear_log_context,
    get_log_context,
    set_log_context,
)


class TestLogContext:
    def setup_method(self):
        clear_log_context()

    def teardown_method(self):
        clear_log_context()

    def test_empty_by_default(self):
        assert get_log_context() == {}

    def test_set_and_get(self):
        set_log_context(request_id="abc", user="bob")
        ctx = get_log_context()
        assert ctx["request_id"] == "abc"
        assert ctx["user"] == "bob"

    def test_set_merges_fields(self):
        set_log_context(a="1")
        set_log_context(b="2")
        ctx = get_log_context()
        assert ctx == {"a": "1", "b": "2"}

    def test_set_ignores_none_values(self):
        set_log_context(a="1", b=None)
        ctx = get_log_context()
        assert "b" not in ctx
        assert ctx["a"] == "1"

    def test_clear_all(self):
        set_log_context(a="1", b="2")
        clear_log_context()
        assert get_log_context() == {}

    def test_clear_specific_keys(self):
        set_log_context(a="1", b="2", c="3")
        clear_log_context("a", "c")
        ctx = get_log_context()
        assert ctx == {"b": "2"}

    def test_clear_nonexistent_key(self):
        set_log_context(a="1")
        clear_log_context("nonexistent")
        assert get_log_context() == {"a": "1"}

    def test_get_returns_copy(self):
        set_log_context(x="1")
        ctx = get_log_context()
        ctx["y"] = "2"
        assert "y" not in get_log_context()
