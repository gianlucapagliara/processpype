"""Configuration manager for ProcessPype."""

import asyncio
from typing import Any

from processpype.core.configuration.models import ApplicationConfiguration

from .providers import ConfigurationProvider, EnvProvider, FileProvider


class ConfigurationManager:
    """Configuration manager for ProcessPype."""

    def __init__(self) -> None:
        """Initialize manager."""
        self._providers: list[ConfigurationProvider] = []
        self._config: dict[str, Any] = {}
        self._initialized = False
        self._lock = asyncio.Lock()

    @classmethod
    async def load_application_config(
        cls, config_file: str | None = None, **kwargs: Any
    ) -> ApplicationConfiguration:
        """Load application configuration from file and/or kwargs.

        Args:
            config_file: Optional path to configuration file
            **kwargs: Configuration overrides

        Returns:
            ApplicationConfiguration instance
        """
        # Create base configuration from kwargs
        config = ApplicationConfiguration(**kwargs)

        # If no config file, return the kwargs-based config
        if not config_file:
            return config

        # Create manager and setup providers
        manager = cls()
        if config_file:
            await manager.add_provider(FileProvider(config_file))
        await manager.add_provider(EnvProvider())

        # Initialize and load configuration
        await manager.initialize()

        # Return loaded configuration
        return manager.get_model(ApplicationConfiguration)

    def has_providers(self) -> bool:
        """Check if there are any providers registered.

        Returns:
            True if there are providers registered, False otherwise
        """
        return len(self._providers) > 0

    async def add_provider(self, provider: ConfigurationProvider) -> None:
        """Add configuration provider.

        Args:
            provider: Configuration provider
        """
        async with self._lock:
            self._providers.append(provider)
            if self._initialized:
                # Load configuration from the new provider
                provider_config = await provider.load()
                self._config.update(provider_config)

    async def initialize(self) -> None:
        """Initialize configuration manager."""
        if self._initialized:
            return

        async with self._lock:
            if not self._initialized:  # Double-check inside lock
                # Load configuration from all providers in reverse order
                config: dict[str, Any] = {}
                for provider in reversed(self._providers):
                    provider_config = await provider.load()
                    config.update(provider_config)
                self._config = config
                self._initialized = True

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self._config.get(key, default)

    def get_model(
        self, model: type[ApplicationConfiguration]
    ) -> ApplicationConfiguration:
        """Get configuration as model.

        Args:
            model: Configuration model class

        Returns:
            Configuration model instance
        """
        return model.model_validate(self._config)

    async def set(self, key: str, value: Any, save: bool = True) -> None:
        """Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value
            save: Whether to save to providers
        """
        async with self._lock:
            self._config[key] = value
            if save:
                for provider in self._providers:
                    await provider.save(self._config)
