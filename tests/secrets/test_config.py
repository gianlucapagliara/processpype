"""Tests for secrets-related configuration models."""

import pytest

from processpype.config.models import (
    AWSBackendConfig,
    DotenvBackendConfig,
    EnvBackendConfig,
    FileBackendConfig,
    ProcessPypeConfig,
    SecretsConfig,
)


class TestSecretsConfig:
    """Tests for SecretsConfig parsing."""

    def test_defaults(self) -> None:
        cfg = SecretsConfig()
        assert cfg.enabled is False
        assert cfg.backends == {}
        assert cfg.load == []
        assert cfg.cache_enabled is True

    def test_from_dict(self) -> None:
        cfg = SecretsConfig(
            enabled=True,
            backends={"myenv": {"type": "env"}},
            load=["myenv:*"],
            cache_enabled=False,
        )
        assert cfg.enabled is True
        assert "myenv" in cfg.backends
        assert cfg.cache_enabled is False

    def test_load_validator_rejects_no_colon(self) -> None:
        with pytest.raises(ValueError, match="must be 'backend_name:pattern'"):
            SecretsConfig(load=["missing_colon"])

    def test_load_validator_accepts_valid(self) -> None:
        cfg = SecretsConfig(load=["env:MY_KEY", "aws:prod/*"])
        assert len(cfg.load) == 2


class TestBackendConfigDiscriminator:
    """Tests for BackendConfig discriminated union resolution."""

    def test_aws_backend(self) -> None:
        cfg = SecretsConfig(backends={"a": {"type": "aws", "region_name": "us-east-1"}})
        backend = cfg.backends["a"]
        assert isinstance(backend, AWSBackendConfig)
        assert backend.region_name == "us-east-1"
        assert backend.prefix == ""

    def test_env_backend(self) -> None:
        cfg = SecretsConfig(backends={"e": {"type": "env", "prefix": "APP_"}})
        backend = cfg.backends["e"]
        assert isinstance(backend, EnvBackendConfig)
        assert backend.prefix == "APP_"

    def test_file_backend(self) -> None:
        cfg = SecretsConfig(backends={"f": {"type": "file", "path": "/tmp/s.yaml"}})
        backend = cfg.backends["f"]
        assert isinstance(backend, FileBackendConfig)
        assert backend.path == "/tmp/s.yaml"

    def test_dotenv_backend(self) -> None:
        cfg = SecretsConfig(backends={"d": {"type": "dotenv", "path": ".env.local"}})
        backend = cfg.backends["d"]
        assert isinstance(backend, DotenvBackendConfig)
        assert backend.path == ".env.local"

    def test_dotenv_default_path(self) -> None:
        cfg = SecretsConfig(backends={"d": {"type": "dotenv"}})
        assert cfg.backends["d"].path == ".env"


class TestPrefixDefaults:
    """Tests for prefix field defaults and values."""

    def test_aws_prefix_default(self) -> None:
        cfg = AWSBackendConfig()
        assert cfg.prefix == ""

    def test_env_prefix_default(self) -> None:
        cfg = EnvBackendConfig()
        assert cfg.prefix == ""

    def test_file_prefix_with_value(self) -> None:
        cfg = FileBackendConfig(prefix="myapp/")
        assert cfg.prefix == "myapp/"

    def test_dotenv_prefix_with_value(self) -> None:
        cfg = DotenvBackendConfig(prefix="PREFIX_")
        assert cfg.prefix == "PREFIX_"


class TestProcessPypeConfigWithSecrets:
    """Tests for ProcessPypeConfig including a secrets section."""

    def test_secrets_section_parsed(self) -> None:
        cfg = ProcessPypeConfig(
            secrets={
                "enabled": True,
                "backends": {
                    "env": {"type": "env"},
                    "local": {"type": "file", "path": "secrets.yaml"},
                },
                "load": ["env:API_KEY", "local:*"],
            }
        )
        assert cfg.secrets.enabled is True
        assert len(cfg.secrets.backends) == 2
        assert isinstance(cfg.secrets.backends["env"], EnvBackendConfig)
        assert isinstance(cfg.secrets.backends["local"], FileBackendConfig)
        assert cfg.secrets.load == ["env:API_KEY", "local:*"]

    def test_default_secrets_section(self) -> None:
        cfg = ProcessPypeConfig()
        assert cfg.secrets.enabled is False
        assert cfg.secrets.backends == {}
