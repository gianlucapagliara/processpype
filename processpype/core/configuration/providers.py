"""Configuration providers for ProcessPype."""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import yaml


class ConfigurationProvider(ABC):
    """Base configuration provider."""

    @abstractmethod
    async def load(self) -> dict[str, Any]:
        """Load configuration from source.

        Returns:
            Configuration dictionary
        """
        pass

    @abstractmethod
    async def save(self, config: dict[str, Any]) -> None:
        """Save configuration to source.

        Args:
            config: Configuration dictionary
        """
        pass


class EnvProvider(ConfigurationProvider):
    """Environment variable configuration provider."""

    def __init__(self, prefix: str = "PROCESSPYPE_"):
        """Initialize provider.

        Args:
            prefix: Environment variable prefix
        """
        self.prefix = prefix

    async def load(self) -> dict[str, Any]:
        """Load configuration from environment variables.

        Returns:
            Configuration dictionary
        """
        config: dict[str, Any] = {}
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                # Remove prefix and convert to lowercase
                key = key[len(self.prefix) :].lower()
                # Split by double underscore for nested keys
                parts = key.split("__")

                # Build nested dictionary
                current = config
                for part in parts[:-1]:
                    current = current.setdefault(part, {})
                current[parts[-1]] = value

        return config

    async def save(self, config: dict[str, Any]) -> None:
        """Save configuration to environment variables.

        Args:
            config: Configuration dictionary
        """
        # Environment variables are read-only
        pass


class FileProvider(ConfigurationProvider):
    """File-based configuration provider."""

    def __init__(self, path: str | Path):
        """Initialize provider.

        Args:
            path: Configuration file path
        """
        self.path = Path(path)

    async def load(self) -> dict[str, Any]:
        """Load configuration from file.

        Returns:
            Configuration dictionary
        """
        if not self.path.exists():
            return {}

        with open(self.path) as f:
            return yaml.safe_load(f) or {}

    async def save(self, config: dict[str, Any]) -> None:
        """Save configuration to file.

        Args:
            config: Configuration dictionary
        """
        # Create parent directories if they don't exist
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.path, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)
