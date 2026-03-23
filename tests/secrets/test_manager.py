"""Tests for SecretsManager and related utilities."""

from pathlib import Path
from typing import Any

import pytest
import yaml

from processpype.config.models import SecretsConfig
from processpype.secrets.exceptions import SecretNotFoundError, SecretsBackendError
from processpype.secrets.manager import (
    SecretsManager,
    _Backend,
    _split_declaration,
    create_secrets_manager,
)
from processpype.secrets.providers import SecretsProvider

# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------


class MockProvider(SecretsProvider):
    """In-memory secrets provider for testing."""

    def __init__(self, data: dict[str, str | dict[str, Any]] | None = None) -> None:
        self._data: dict[str, str | dict[str, Any]] = data or {}

    def get_secret(self, name: str, *, raw: bool = False) -> str | dict[str, Any]:
        if name not in self._data:
            raise SecretNotFoundError(f"Mock: '{name}' not found")
        value = self._data[name]
        if raw:
            return value if isinstance(value, str) else str(value)
        return value

    def list_secrets(self, pattern: str) -> list[str]:
        from fnmatch import fnmatch

        return [k for k in self._data if fnmatch(k, pattern)]


# ---------------------------------------------------------------------------
# _Backend tests
# ---------------------------------------------------------------------------


class TestBackend:
    """Tests for the _Backend wrapper."""

    def test_full_name_no_prefix(self) -> None:
        backend = _Backend(MockProvider(), prefix="")
        assert backend.full_name("key") == "key"

    def test_full_name_with_prefix(self) -> None:
        backend = _Backend(MockProvider(), prefix="prod/app")
        assert backend.full_name("key") == "prod/app/key"

    def test_prefix_normalisation(self) -> None:
        backend = _Backend(MockProvider(), prefix="prod/app/")
        assert backend.prefix == "prod/app/"
        assert backend.full_name("key") == "prod/app/key"

    def test_strip_prefix(self) -> None:
        backend = _Backend(MockProvider(), prefix="prod")
        assert backend.strip_prefix("prod/key") == "key"

    def test_strip_prefix_no_match(self) -> None:
        backend = _Backend(MockProvider(), prefix="prod")
        assert backend.strip_prefix("other/key") == "other/key"

    def test_list_secrets_prefix_handling(self) -> None:
        provider = MockProvider({"pfx/a": "1", "pfx/b": "2", "other": "3"})
        backend = _Backend(provider, prefix="pfx")
        result = backend.list_secrets("*")
        assert sorted(result) == ["a", "b"]


# ---------------------------------------------------------------------------
# SecretsManager tests
# ---------------------------------------------------------------------------


class TestSecretsManager:
    """Tests for SecretsManager."""

    def _make_manager(
        self, data: dict[str, str | dict[str, Any]] | None = None
    ) -> SecretsManager:
        provider = MockProvider(data or {"key1": "val1", "key2": "val2"})
        backends = {"mock": _Backend(provider)}
        return SecretsManager(backends)

    def test_get_from_cache(self) -> None:
        manager = self._make_manager()
        # Prime cache
        val = manager.get("mock:key1")
        assert val == "val1"
        # Second call should hit cache (provider could be swapped out)
        assert manager.get("mock:key1") == "val1"

    def test_get_on_demand(self) -> None:
        manager = self._make_manager()
        assert manager.get("mock:key2") == "val2"

    def test_get_or_none_found(self) -> None:
        manager = self._make_manager()
        assert manager.get_or_none("mock:key1") == "val1"

    def test_get_or_none_not_found(self) -> None:
        manager = self._make_manager()
        assert manager.get_or_none("mock:missing") is None

    def test_raw_bypasses_cache(self) -> None:
        manager = self._make_manager()
        # Prime the cache with parsed value
        manager.get("mock:key1")
        assert "mock:key1" in manager._cache
        # raw=True should bypass cache and fetch fresh
        raw_val = manager.get("mock:key1", raw=True)
        assert raw_val == "val1"

    def test_invalidate(self) -> None:
        manager = self._make_manager()
        manager.get("mock:key1")
        assert "mock:key1" in manager._cache
        manager.invalidate("mock:key1")
        assert "mock:key1" not in manager._cache

    def test_clear_cache(self) -> None:
        manager = self._make_manager()
        manager.get("mock:key1")
        manager.get("mock:key2")
        assert len(manager._cache) == 2
        manager.clear_cache()
        assert len(manager._cache) == 0

    def test_get_unknown_backend_raises(self) -> None:
        manager = self._make_manager()
        with pytest.raises(SecretNotFoundError, match="Unknown backend"):
            manager.get("nope:key")


# ---------------------------------------------------------------------------
# SecretsManager.load() tests
# ---------------------------------------------------------------------------


class TestSecretsManagerLoad:
    """Tests for SecretsManager.load()."""

    def test_successful_preload(self) -> None:
        provider = MockProvider({"a": "1", "b": "2"})
        backends = {"src": _Backend(provider)}
        manager = SecretsManager(backends)
        manager.load(["src:*"])
        assert manager._cache["src:a"] == "1"
        assert manager._cache["src:b"] == "2"

    def test_partial_failure_resilience(self) -> None:
        """Some keys fail but not all — should not raise."""

        class PartialProvider(MockProvider):
            def get_secret(
                self, name: str, *, raw: bool = False
            ) -> str | dict[str, Any]:
                if name == "bad":
                    raise SecretNotFoundError("gone")
                return super().get_secret(name, raw=raw)

        provider = PartialProvider({"good": "ok", "bad": "x"})
        backends = {"p": _Backend(provider)}
        manager = SecretsManager(backends)
        manager.load(["p:*"])
        assert "p:good" in manager._cache
        assert "p:bad" not in manager._cache

    def test_all_fail_raises(self) -> None:
        """When every key in a declaration fails, raise SecretsBackendError."""

        class AlwaysFailProvider(MockProvider):
            def get_secret(
                self, name: str, *, raw: bool = False
            ) -> str | dict[str, Any]:
                raise SecretsBackendError("boom")

        provider = AlwaysFailProvider({"a": "1", "b": "2"})
        backends = {"fail": _Backend(provider)}
        manager = SecretsManager(backends)
        with pytest.raises(SecretsBackendError, match="All secrets failed"):
            manager.load(["fail:*"])

    def test_unknown_backend_in_load_raises(self) -> None:
        manager = SecretsManager({})
        with pytest.raises(SecretsBackendError, match="Unknown backend"):
            manager.load(["nonexistent:*"])


# ---------------------------------------------------------------------------
# _split_declaration tests
# ---------------------------------------------------------------------------


class TestSplitDeclaration:
    """Tests for _split_declaration."""

    def test_valid_input(self) -> None:
        assert _split_declaration("aws:prod/*") == ("aws", "prod/*")

    def test_colon_in_pattern(self) -> None:
        assert _split_declaration("backend:a:b") == ("backend", "a:b")

    def test_missing_colon_raises(self) -> None:
        with pytest.raises(ValueError, match="expected 'backend_name:pattern'"):
            _split_declaration("no_colon_here")


# ---------------------------------------------------------------------------
# create_secrets_manager tests
# ---------------------------------------------------------------------------


class TestCreateSecretsManager:
    """Tests for the create_secrets_manager factory."""

    def test_with_env_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_CSM_KEY", "envval")
        config = SecretsConfig(
            enabled=True,
            backends={"myenv": {"type": "env"}},
            load=["myenv:TEST_CSM_KEY"],
        )
        manager = create_secrets_manager(config)
        assert manager.get("myenv:TEST_CSM_KEY") == "envval"

    def test_with_file_backend(self, tmp_path: Path) -> None:
        secrets_file = tmp_path / "secrets.yaml"
        secrets_file.write_text(yaml.safe_dump({"db_pass": "filepass"}))
        config = SecretsConfig(
            enabled=True,
            backends={"local": {"type": "file", "path": str(secrets_file)}},
            load=["local:*"],
        )
        manager = create_secrets_manager(config)
        assert manager.get("local:db_pass") == "filepass"

    def test_unknown_backend_type_raises(self) -> None:
        config = SecretsConfig(
            enabled=True,
            backends={"bad": {"type": "env"}},
        )
        # Manually patch the type to something unknown after validation
        backend = config.backends["bad"]
        object.__setattr__(backend, "type", "nosuchtype")
        with pytest.raises(SecretsBackendError, match="Unknown backend type"):
            create_secrets_manager(config)

    def test_no_load_declarations(self) -> None:
        config = SecretsConfig(
            enabled=True,
            backends={"e": {"type": "env"}},
            load=[],
        )
        manager = create_secrets_manager(config)
        assert len(manager._cache) == 0
