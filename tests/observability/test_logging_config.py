"""Tests for logging configuration models and helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from processpype.observability.logging.config import (
    DictConfigModel,
    LoggingRuntimeContext,
    _replace_tokens,
    build_runtime_context,
    load_logging_config,
    load_logging_config_from_path,
    resolve_project_root,
)


class TestLoggingRuntimeContext:
    def test_is_frozen_dataclass(self):
        ctx = LoggingRuntimeContext(
            project_dir="/tmp",
            strategy_code="test",
            run_id="r1",
            instance_id="i1",
            environment="dev",
        )
        assert ctx.project_dir == "/tmp"
        assert ctx.strategy_code == "test"
        with pytest.raises(AttributeError):
            ctx.project_dir = "/other"


class TestResolveProjectRoot:
    def test_uses_env_var_when_set(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
        assert resolve_project_root() == tmp_path.resolve()

    def test_falls_back_to_cwd(self, monkeypatch):
        monkeypatch.delenv("PROJECT_DIR", raising=False)
        assert resolve_project_root() == Path.cwd().resolve()


class TestBuildRuntimeContext:
    def test_basic(self, monkeypatch):
        monkeypatch.delenv("RUN_ID", raising=False)
        monkeypatch.delenv("INSTANCE_ID", raising=False)
        monkeypatch.delenv("DEPLOY_ENV", raising=False)
        monkeypatch.delenv("PROJECT_DIR", raising=False)
        ctx = build_runtime_context("my_strategy.yml")
        assert ctx.strategy_code == "my_strategy"
        assert ctx.environment == "development"
        assert ctx.run_id  # non-empty
        assert ctx.instance_id  # non-empty

    def test_with_env_vars(self, monkeypatch):
        monkeypatch.setenv("RUN_ID", "custom_run")
        monkeypatch.setenv("INSTANCE_ID", "custom_instance")
        monkeypatch.setenv("DEPLOY_ENV", "production")
        ctx = build_runtime_context()
        assert ctx.run_id == "custom_run"
        assert ctx.instance_id == "custom_instance"
        assert ctx.environment == "production"

    def test_default_strategy(self, monkeypatch):
        monkeypatch.delenv("RUN_ID", raising=False)
        monkeypatch.delenv("INSTANCE_ID", raising=False)
        monkeypatch.delenv("DEPLOY_ENV", raising=False)
        ctx = build_runtime_context()
        assert ctx.strategy_code == "application"


class TestReplaceTokens:
    def test_replaces_in_string(self):
        result = _replace_tokens("dir=$PROJECT_DIR", {"$PROJECT_DIR": "/home"})
        assert result == "dir=/home"

    def test_replaces_in_dict(self):
        result = _replace_tokens({"k": "$TOKEN"}, {"$TOKEN": "val"})
        assert result == {"k": "val"}

    def test_replaces_in_list(self):
        result = _replace_tokens(["$A", "$B"], {"$A": "1", "$B": "2"})
        assert result == ["1", "2"]

    def test_passthrough_non_string(self):
        assert _replace_tokens(42, {"$X": "y"}) == 42
        assert _replace_tokens(None, {"$X": "y"}) is None


class TestDictConfigModel:
    def test_valid_config(self):
        m = DictConfigModel(
            version=1,
            root={"level": "INFO", "handlers": ["console"]},
            handlers={"console": {"class": "logging.StreamHandler"}},
        )
        assert m.version == 1

    def test_invalid_version(self):
        with pytest.raises(ValueError, match="version=1"):
            DictConfigModel(
                version=2,
                root={"level": "INFO"},
            )


class TestLoadLoggingConfig:
    def test_file_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
        with pytest.raises(FileNotFoundError):
            load_logging_config("nonexistent.yaml")

    def test_loads_valid_config(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
        conf_dir = tmp_path / ".conf"
        conf_dir.mkdir()
        config_data = {
            "version": 1,
            "root": {"level": "INFO", "handlers": ["console"]},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                }
            },
        }
        config_file = conf_dir / "logging.yaml"
        config_file.write_text(yaml.dump(config_data))

        result, ctx = load_logging_config("logging.yaml")
        assert result["version"] == 1
        assert ctx.project_dir == str(tmp_path.resolve())

    def test_token_replacement(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
        conf_dir = tmp_path / ".conf"
        conf_dir.mkdir()
        config_data = {
            "version": 1,
            "root": {"level": "INFO", "handlers": []},
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": "$PROJECT_DIR/app.log",
                }
            },
        }
        config_file = conf_dir / "logging.yaml"
        config_file.write_text(yaml.dump(config_data))

        result, ctx = load_logging_config("logging.yaml")
        assert str(tmp_path.resolve()) in result["handlers"]["file"]["filename"]

    def test_invalid_yaml_content(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
        conf_dir = tmp_path / ".conf"
        conf_dir.mkdir()
        config_file = conf_dir / "logging.yaml"
        config_file.write_text("just a string")

        with pytest.raises(ValueError, match="dictionary"):
            load_logging_config("logging.yaml")

    def test_invalid_dictconfig_schema(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
        conf_dir = tmp_path / ".conf"
        conf_dir.mkdir()
        config_data = {
            "version": 2,  # invalid
            "root": {"level": "INFO"},
        }
        config_file = conf_dir / "logging.yaml"
        config_file.write_text(yaml.dump(config_data))

        with pytest.raises(ValueError, match="Invalid"):
            load_logging_config("logging.yaml")

    def test_custom_file_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
        custom_dir = tmp_path / "custom_conf"
        custom_dir.mkdir()
        config_data = {
            "version": 1,
            "root": {"level": "DEBUG", "handlers": []},
        }
        config_file = custom_dir / "log.yaml"
        config_file.write_text(yaml.dump(config_data))

        result, _ = load_logging_config("log.yaml", file_dir=str(custom_dir))
        assert result["version"] == 1

    def test_extra_replace_mapping(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
        conf_dir = tmp_path / ".conf"
        conf_dir.mkdir()
        config_data = {
            "version": 1,
            "root": {"level": "INFO", "handlers": []},
            "formatters": {"custom": {"format": "$CUSTOM_VAR"}},
        }
        config_file = conf_dir / "logging.yaml"
        config_file.write_text(yaml.dump(config_data))

        result, _ = load_logging_config(
            "logging.yaml", replace_mapping={"$CUSTOM_VAR": "replaced"}
        )
        assert result["formatters"]["custom"]["format"] == "replaced"


class TestLoadLoggingConfigFromPath:
    def test_loads_from_resolved_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
        config_data = {
            "version": 1,
            "root": {"level": "INFO", "handlers": ["console"]},
            "handlers": {
                "console": {"class": "logging.StreamHandler", "level": "INFO"}
            },
        }
        config_file = tmp_path / "logging.yaml"
        config_file.write_text(yaml.dump(config_data))

        result, ctx = load_logging_config_from_path(config_file)
        assert result["version"] == 1
        assert ctx.project_dir == str(tmp_path.resolve())

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_logging_config_from_path(tmp_path / "nonexistent.yaml")

    def test_token_replacement(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
        config_data = {
            "version": 1,
            "root": {"level": "INFO", "handlers": []},
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": "$PROJECT_DIR/app.log",
                }
            },
        }
        config_file = tmp_path / "logging.yaml"
        config_file.write_text(yaml.dump(config_data))

        result, _ = load_logging_config_from_path(config_file)
        assert str(tmp_path.resolve()) in result["handlers"]["file"]["filename"]
