"""Tests for configuration providers."""

from pathlib import Path

import pytest
import yaml

from processpype.config.providers import (
    ConfigurationProvider,
    FileProvider,
    replace_env_tokens,
)


class TestReplaceEnvTokens:
    """Tests for the replace_env_tokens helper."""

    def test_plain_string_unchanged(self) -> None:
        assert replace_env_tokens("hello world") == "hello world"

    def test_non_string_passthrough(self) -> None:
        assert replace_env_tokens(42) == 42
        assert replace_env_tokens(True) is True
        assert replace_env_tokens(None) is None

    def test_env_var_substitution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_PP_VAR", "replaced")
        assert replace_env_tokens("${TEST_PP_VAR}") == "replaced"

    def test_env_var_with_default_uses_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEST_PP_VAR", "from_env")
        assert replace_env_tokens("${TEST_PP_VAR:-fallback}") == "from_env"

    def test_env_var_with_default_uses_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("TEST_PP_MISSING", raising=False)
        assert replace_env_tokens("${TEST_PP_MISSING:-fallback}") == "fallback"

    def test_env_var_missing_no_default_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("TEST_PP_MISSING", raising=False)
        with pytest.raises(ValueError, match="not set and no default"):
            replace_env_tokens("${TEST_PP_MISSING}")

    def test_dict_recursion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_PP_KEY", "val")
        result = replace_env_tokens({"a": "${TEST_PP_KEY}", "b": "plain"})
        assert result == {"a": "val", "b": "plain"}

    def test_list_recursion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_PP_ITEM", "x")
        result = replace_env_tokens(["${TEST_PP_ITEM}", "y"])
        assert result == ["x", "y"]

    def test_embedded_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_PP_HOST", "localhost")
        assert (
            replace_env_tokens("http://${TEST_PP_HOST}:8080") == "http://localhost:8080"
        )


class TestConfigurationProviderABC:
    """Tests for the abstract base class."""

    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            ConfigurationProvider()  # type: ignore[abstract]


class TestFileProvider:
    """Tests for FileProvider."""

    @pytest.mark.asyncio
    async def test_load_missing_file_returns_empty(self, tmp_path: Path) -> None:
        provider = FileProvider(tmp_path / "nonexistent.yaml")
        result = await provider.load()
        assert result == {}

    @pytest.mark.asyncio
    async def test_load_valid_yaml(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.safe_dump({"app": {"title": "My App", "debug": True}}))
        provider = FileProvider(cfg_file)
        result = await provider.load()
        assert result["app"]["title"] == "My App"
        assert result["app"]["debug"] is True

    @pytest.mark.asyncio
    async def test_load_with_env_substitution(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEST_PP_TITLE", "EnvTitle")
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("app:\n  title: ${TEST_PP_TITLE}\n")
        provider = FileProvider(cfg_file)
        result = await provider.load()
        assert result["app"]["title"] == "EnvTitle"

    @pytest.mark.asyncio
    async def test_load_empty_yaml_returns_empty(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "empty.yaml"
        cfg_file.write_text("")
        provider = FileProvider(cfg_file)
        result = await provider.load()
        assert result == {}

    @pytest.mark.asyncio
    async def test_save_creates_file(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "sub" / "config.yaml"
        provider = FileProvider(cfg_file)
        await provider.save({"app": {"title": "Saved"}})

        assert cfg_file.exists()
        loaded = yaml.safe_load(cfg_file.read_text())
        assert loaded["app"]["title"] == "Saved"

    @pytest.mark.asyncio
    async def test_save_overwrites(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.safe_dump({"old": True}))
        provider = FileProvider(cfg_file)
        await provider.save({"new": True})
        loaded = yaml.safe_load(cfg_file.read_text())
        assert "old" not in loaded
        assert loaded["new"] is True

    def test_init_converts_str_to_path(self) -> None:
        provider = FileProvider("/some/path.yaml")
        assert isinstance(provider.path, Path)


class TestResolveSecretTokens:
    """Tests for the resolve_secret_tokens helper."""

    def test_plain_string_unchanged(self) -> None:
        from processpype.config.providers import resolve_secret_tokens

        assert resolve_secret_tokens("hello", None) == "hello"

    def test_non_string_passthrough(self) -> None:
        from processpype.config.providers import resolve_secret_tokens

        assert resolve_secret_tokens(42, None) == 42
        assert resolve_secret_tokens(True, None) is True
        assert resolve_secret_tokens(None, None) is None

    def test_secret_token_replaced(self) -> None:
        from unittest.mock import MagicMock

        from processpype.config.providers import resolve_secret_tokens

        sm = MagicMock()
        sm.get.return_value = "resolved_value"
        result = resolve_secret_tokens("${secret://aws:my_key}", sm)
        assert result == "resolved_value"
        sm.get.assert_called_once_with("aws:my_key")

    def test_secret_token_dict_value_coerced(self) -> None:
        from unittest.mock import MagicMock

        from processpype.config.providers import resolve_secret_tokens

        sm = MagicMock()
        sm.get.return_value = {"user": "admin"}
        result = resolve_secret_tokens("${secret://aws:creds}", sm)
        assert result == "{'user': 'admin'}"

    def test_dict_recursion(self) -> None:
        from unittest.mock import MagicMock

        from processpype.config.providers import resolve_secret_tokens

        sm = MagicMock()
        sm.get.return_value = "secret_val"
        result = resolve_secret_tokens({"a": "${secret://env:key}", "b": "plain"}, sm)
        assert result == {"a": "secret_val", "b": "plain"}

    def test_list_recursion(self) -> None:
        from unittest.mock import MagicMock

        from processpype.config.providers import resolve_secret_tokens

        sm = MagicMock()
        sm.get.return_value = "x"
        result = resolve_secret_tokens(["${secret://env:k}", "y"], sm)
        assert result == ["x", "y"]

    def test_embedded_token(self) -> None:
        from unittest.mock import MagicMock

        from processpype.config.providers import resolve_secret_tokens

        sm = MagicMock()
        sm.get.return_value = "s3cret"
        result = resolve_secret_tokens("pw=${secret://env:pw}", sm)
        assert result == "pw=s3cret"

    def test_no_token_no_manager_call(self) -> None:
        from unittest.mock import MagicMock

        from processpype.config.providers import resolve_secret_tokens

        sm = MagicMock()
        resolve_secret_tokens("no tokens here", sm)
        sm.get.assert_not_called()
