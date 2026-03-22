"""Tests for the main module."""

from unittest.mock import MagicMock, patch

from processpype.application import Application


def test_main_module_creates_app() -> None:
    """Test that importing main creates an Application via ApplicationCreator."""
    mock_app = MagicMock(spec=Application)
    with patch(
        "processpype.creator.ApplicationCreator.get_application",
        return_value=mock_app,
    ):
        # Re-import to trigger module-level code
        import importlib

        import processpype.main

        importlib.reload(processpype.main)
        assert processpype.main.app is mock_app
