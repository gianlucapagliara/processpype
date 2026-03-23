"""Tests for secrets providers."""

import json
import logging
from pathlib import Path

import pytest
import yaml

from processpype.secrets.exceptions import SecretNotFoundError, SecretsBackendError
from processpype.secrets.providers import (
    DotenvProvider,
    EnvironmentProvider,
    FileSecretsProvider,
    SecretsProvider,
)


class TestSecretsProviderABC:
    """Tests for the abstract base class."""

    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            SecretsProvider()  # type: ignore[abstract]


class TestEnvironmentProvider:
    """Tests for EnvironmentProvider."""

    def test_get_existing_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_SECRET_KEY", "secret_value")
        provider = EnvironmentProvider()
        assert provider.get_secret("TEST_SECRET_KEY") == "secret_value"

    def test_get_missing_key(self) -> None:
        provider = EnvironmentProvider()
        with pytest.raises(SecretNotFoundError, match="not set"):
            provider.get_secret("DEFINITELY_MISSING_KEY_XYZ_123")

    def test_get_json_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "TEST_JSON_SECRET", json.dumps({"user": "admin", "pass": "pw"})
        )
        provider = EnvironmentProvider()
        result = provider.get_secret("TEST_JSON_SECRET")
        assert isinstance(result, dict)
        assert result["user"] == "admin"

    def test_get_raw_skips_json_parsing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_RAW", json.dumps({"key": "val"}))
        provider = EnvironmentProvider()
        result = provider.get_secret("TEST_RAW", raw=True)
        assert isinstance(result, str)
        assert result == json.dumps({"key": "val"})

    def test_list_secrets_with_glob(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_SEC_A", "1")
        monkeypatch.setenv("TEST_SEC_B", "2")
        provider = EnvironmentProvider()
        matches = provider.list_secrets("TEST_SEC_*")
        assert "TEST_SEC_A" in matches
        assert "TEST_SEC_B" in matches


class TestFileSecretsProvider:
    """Tests for FileSecretsProvider."""

    def test_get_key(self, tmp_path: Path) -> None:
        secrets_file = tmp_path / "secrets.yaml"
        secrets_file.write_text(yaml.safe_dump({"db_password": "s3cret"}))
        provider = FileSecretsProvider(secrets_file)
        assert provider.get_secret("db_password") == "s3cret"

    def test_missing_key(self, tmp_path: Path) -> None:
        secrets_file = tmp_path / "secrets.yaml"
        secrets_file.write_text(yaml.safe_dump({"existing": "value"}))
        provider = FileSecretsProvider(secrets_file)
        with pytest.raises(SecretNotFoundError, match="not found"):
            provider.get_secret("nonexistent")

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        provider = FileSecretsProvider(tmp_path / "nope.yaml")
        with pytest.raises(SecretsBackendError, match="not found"):
            provider.get_secret("any_key")

    def test_env_token_error_wrapped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("MISSING_TOKEN_VAR", raising=False)
        secrets_file = tmp_path / "secrets.yaml"
        secrets_file.write_text("key: ${MISSING_TOKEN_VAR}\n")
        provider = FileSecretsProvider(secrets_file)
        with pytest.raises(SecretsBackendError, match="Failed to process"):
            provider.get_secret("key")

    def test_list_secrets_glob(self, tmp_path: Path) -> None:
        secrets_file = tmp_path / "secrets.yaml"
        secrets_file.write_text(
            yaml.safe_dump({"db_host": "h", "db_port": "p", "api_key": "k"})
        )
        provider = FileSecretsProvider(secrets_file)
        matches = provider.list_secrets("db_*")
        assert sorted(matches) == ["db_host", "db_port"]

    def test_raw_returns_string(self, tmp_path: Path) -> None:
        secrets_file = tmp_path / "secrets.yaml"
        secrets_file.write_text(yaml.safe_dump({"num": 42}))
        provider = FileSecretsProvider(secrets_file)
        result = provider.get_secret("num", raw=True)
        assert result == "42"


class TestDotenvProvider:
    """Tests for DotenvProvider."""

    def test_basic_key_value(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("MY_KEY=my_value\n")
        provider = DotenvProvider(env_file)
        assert provider.get_secret("MY_KEY") == "my_value"

    def test_quoted_values(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("SINGLE='single val'\nDOUBLE=\"double val\"\n")
        provider = DotenvProvider(env_file)
        assert provider.get_secret("SINGLE") == "single val"
        assert provider.get_secret("DOUBLE") == "double val"

    def test_export_prefix(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("export EXPORTED_KEY=exported_value\n")
        provider = DotenvProvider(env_file)
        assert provider.get_secret("EXPORTED_KEY") == "exported_value"

    def test_comments_and_blank_lines(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nKEY=value\n\n# another\n")
        provider = DotenvProvider(env_file)
        assert provider.get_secret("KEY") == "value"
        matches = provider.list_secrets("*")
        assert matches == ["KEY"]

    def test_escape_sequences_in_double_quotes(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text('ESC="line1\\nline2\\ttab\\\\backslash"\n')
        provider = DotenvProvider(env_file)
        result = provider.get_secret("ESC")
        assert result == "line1\nline2\ttab\\backslash"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        provider = DotenvProvider(tmp_path / "missing.env")
        with pytest.raises(SecretsBackendError, match="not found"):
            provider.get_secret("ANY")

    def test_list_secrets_glob(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("DB_HOST=h\nDB_PORT=5432\nAPI_KEY=k\n")
        provider = DotenvProvider(env_file)
        matches = provider.list_secrets("DB_*")
        assert sorted(matches) == ["DB_HOST", "DB_PORT"]

    def test_raw_skips_json(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text('DATA={"a": 1}\n')
        provider = DotenvProvider(env_file)
        raw = provider.get_secret("DATA", raw=True)
        assert isinstance(raw, str)
        assert raw == '{"a": 1}'
        parsed = provider.get_secret("DATA")
        assert isinstance(parsed, dict)

    def test_malformed_line_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("GOOD=value\nBADLINE\n")
        with caplog.at_level(logging.WARNING):
            provider = DotenvProvider(env_file)
            assert provider.get_secret("GOOD") == "value"
        assert "malformed" in caplog.text.lower() or "Skipping" in caplog.text

    def test_missing_key_raises(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("A=1\n")
        provider = DotenvProvider(env_file)
        with pytest.raises(SecretNotFoundError, match="not found"):
            provider.get_secret("MISSING")
