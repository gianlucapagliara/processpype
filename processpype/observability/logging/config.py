"""Logging configuration and config file loading."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from hashlib import md5
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

DEFAULT_LOG_FORMAT = (
    "%(asctime)s.%(msecs)03.0f | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
)
DEFAULT_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_DATEFMT_SHORT = "%H:%M:%S"


class DictConfigModel(BaseModel):
    """Pydantic validator for Python's logging.config dictConfig schema."""

    model_config = ConfigDict(extra="allow")

    version: int
    formatters: dict[str, dict[str, Any]] = Field(default_factory=dict)
    filters: dict[str, dict[str, Any]] = Field(default_factory=dict)
    handlers: dict[str, dict[str, Any]] = Field(default_factory=dict)
    loggers: dict[str, dict[str, Any]] = Field(default_factory=dict)
    root: dict[str, Any]

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError("Only logging dictConfig version=1 is supported.")
        return value


@dataclass(frozen=True)
class LoggingRuntimeContext:
    project_dir: str
    strategy_code: str
    run_id: str
    instance_id: str
    environment: str


def resolve_project_root() -> Path:
    env_root = os.environ.get("PROJECT_DIR")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path.cwd().resolve()


def build_runtime_context(
    strategy_file_path: str = "application",
) -> LoggingRuntimeContext:
    project_root = resolve_project_root()
    strategy_code = (strategy_file_path or "application").replace(".yml", "")
    run_id = (
        os.environ.get("RUN_ID")
        or md5(
            f"pid:{os.getpid()}_ppid:{os.getppid()}_strategy:{strategy_code}".encode()
        ).hexdigest()
    )
    instance_id = (
        os.environ.get("INSTANCE_ID")
        or md5(
            f"{platform.uname()}_pid:{os.getpid()}_ppid:{os.getppid()}".encode()
        ).hexdigest()
    )
    environment = os.environ.get("DEPLOY_ENV", "development")
    return LoggingRuntimeContext(
        project_dir=str(project_root),
        strategy_code=strategy_code,
        run_id=run_id,
        instance_id=instance_id,
        environment=environment,
    )


def _replace_tokens(value: Any, replace_mapping: dict[str, str]) -> Any:
    if isinstance(value, str):
        output = value
        for key, token_value in replace_mapping.items():
            output = output.replace(key, token_value)
        return output
    if isinstance(value, dict):
        return {
            key: _replace_tokens(item, replace_mapping) for key, item in value.items()
        }
    if isinstance(value, list):
        return [_replace_tokens(item, replace_mapping) for item in value]
    return value


def _load_yaml_dict(file_path: Path) -> tuple[dict[str, Any], str]:
    with file_path.open("r", encoding="utf-8") as stream:
        source = stream.read()
    loaded = yaml.safe_load(source)
    if not isinstance(loaded, dict):
        raise ValueError(
            f"Logging config must deserialize into a dictionary: {file_path}"
        )
    return loaded, source


def load_logging_config(
    conf_filename: str,
    strategy_file_path: str = "application",
    file_dir: str | None = None,
    replace_mapping: dict[str, str] | None = None,
) -> tuple[dict[str, Any], LoggingRuntimeContext]:
    runtime_context = build_runtime_context(strategy_file_path=strategy_file_path)
    config_dir = (
        Path(file_dir).expanduser()
        if file_dir
        else Path(runtime_context.project_dir) / ".conf"
    )
    if not config_dir.is_absolute():
        config_dir = (Path(runtime_context.project_dir) / config_dir).resolve()
    config_path = (config_dir / conf_filename).resolve()
    if not config_path.is_file():
        raise FileNotFoundError(f"Logging config file not found: {config_path}.")

    config_dict, _ = _load_yaml_dict(config_path)

    runtime_replace_mapping = {
        "$PROJECT_DIR": runtime_context.project_dir,
        "$STRATEGY_FILE_PATH": runtime_context.strategy_code,
        "$RUN_ID": runtime_context.run_id,
        "$INSTANCE_ID": runtime_context.instance_id,
        "$DEPLOY_ENV": runtime_context.environment,
    }
    if replace_mapping:
        runtime_replace_mapping = {**runtime_replace_mapping, **replace_mapping}
    config_dict = _replace_tokens(config_dict, runtime_replace_mapping)

    try:
        validated = DictConfigModel.model_validate(config_dict)
    except ValidationError as exc:
        raise ValueError(f"Invalid logging configuration file: {config_path}") from exc
    return validated.model_dump(mode="python"), runtime_context
