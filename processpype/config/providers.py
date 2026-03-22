"""Configuration providers for ProcessPype.

YAML-first configuration with ${ENV_VAR} token replacement for secrets.
"""

import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import yaml


def _replace_env_tokens(value: Any) -> Any:
    """Recursively replace ${ENV_VAR} and ${ENV_VAR:-default} tokens in strings.

    Supports:
      - ${VAR} — replaced with os.environ["VAR"], raises if not set
      - ${VAR:-default} — replaced with os.environ.get("VAR", "default")
      - $PROJECT_DIR, $RUN_ID, $APP_NAME — replaced from runtime context
    """
    if isinstance(value, str):
        # Handle ${VAR:-default} and ${VAR} patterns
        def _replace_match(match: re.Match[str]) -> str:
            var_name = match.group(1)
            default = match.group(3)  # None if no default specified
            env_val = os.environ.get(var_name)
            if env_val is not None:
                return env_val
            if default is not None:
                return default
            raise ValueError(
                f"Environment variable ${{{var_name}}} is not set and no default provided"
            )

        return re.sub(
            r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-(.*?))?\}", _replace_match, value
        )
    elif isinstance(value, dict):
        return {k: _replace_env_tokens(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_replace_env_tokens(item) for item in value]
    return value


class ConfigurationProvider(ABC):
    """Base configuration provider."""

    @abstractmethod
    async def load(self) -> dict[str, Any]:
        """Load configuration from source."""

    @abstractmethod
    async def save(self, config: dict[str, Any]) -> None:
        """Save configuration to source."""


class FileProvider(ConfigurationProvider):
    """YAML file configuration provider with ${ENV_VAR} token replacement."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    async def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}

        with open(self.path) as f:
            raw = yaml.safe_load(f) or {}

        result: dict[str, Any] = _replace_env_tokens(raw)
        return result

    async def save(self, config: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)
