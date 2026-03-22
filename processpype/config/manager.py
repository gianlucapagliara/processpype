"""Configuration manager for ProcessPype."""

from typing import Any

from .models import ProcessPypeConfig
from .providers import FileProvider


async def load_config(
    config_file: str | None = None, **overrides: Any
) -> ProcessPypeConfig:
    """Load ProcessPypeConfig from a YAML file with optional overrides.

    Args:
        config_file: Path to processpype.yaml. If None, returns defaults + overrides.
        **overrides: Top-level keys to override (e.g. ``app={"debug": True}``).

    Returns:
        Validated ProcessPypeConfig instance.
    """
    data: dict[str, Any] = {}

    if config_file:
        provider = FileProvider(config_file)
        data = await provider.load()

    # Merge overrides (shallow merge at top level)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            data[key] = {**data[key], **value}
        else:
            data[key] = value

    return ProcessPypeConfig.model_validate(data)


class ConfigurationManager:
    """Manages configuration state at runtime.

    For most use-cases, the ``load_config()`` function is sufficient.
    Use ConfigurationManager when you need to mutate or persist config at runtime.
    """

    def __init__(self, config: ProcessPypeConfig) -> None:
        self._config = config

    @property
    def config(self) -> ProcessPypeConfig:
        return self._config

    @classmethod
    async def from_file(
        cls, config_file: str | None = None, **overrides: Any
    ) -> "ConfigurationManager":
        config = await load_config(config_file, **overrides)
        return cls(config)
