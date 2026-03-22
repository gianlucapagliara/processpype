"""Tests for configuration manager."""

from pathlib import Path

import pytest

from processpype.config.manager import load_config
from processpype.config.models import ProcessPypeConfig


class TestLoadConfig:
    """Tests for the load_config function."""

    @pytest.mark.asyncio
    async def test_no_file_returns_defaults(self) -> None:
        config = await load_config()
        assert isinstance(config, ProcessPypeConfig)
        assert config.app.title == "ProcessPype"

    @pytest.mark.asyncio
    async def test_load_from_yaml_file(self, test_config_file: Path) -> None:
        config = await load_config(str(test_config_file))
        assert config.app.title == "Test App"
        assert config.app.version == "1.0.0"
        assert config.app.environment == "testing"
        assert config.app.debug is True
        assert config.server.host == "localhost"
        assert config.server.port == 8080

    @pytest.mark.asyncio
    async def test_overrides_without_file(self) -> None:
        config = await load_config(app={"title": "Override App", "debug": True})
        assert config.app.title == "Override App"
        assert config.app.debug is True

    @pytest.mark.asyncio
    async def test_overrides_merge_with_file(self, test_config_file: Path) -> None:
        config = await load_config(
            str(test_config_file), app={"debug": False, "timezone": "US/Eastern"}
        )
        # File value kept where not overridden
        assert config.app.title == "Test App"
        # Override applied
        assert config.app.debug is False
        assert config.app.timezone == "US/Eastern"

    @pytest.mark.asyncio
    async def test_override_replaces_non_dict(self, test_config_file: Path) -> None:
        config = await load_config(str(test_config_file), server={"port": 9999})
        assert config.server.port == 9999
        # File value merged
        assert config.server.host == "localhost"

    @pytest.mark.asyncio
    async def test_override_non_dict_value(self) -> None:
        """Non-dict override replaces entirely (tests else branch)."""
        config = await load_config(custom_key="value")
        assert config.custom_key == "value"  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        config = await load_config(str(tmp_path / "nonexistent.yaml"))
        assert isinstance(config, ProcessPypeConfig)
        assert config.app.title == "ProcessPype"
