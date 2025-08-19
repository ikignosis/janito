"""
Tests for the plugin system.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from janito.plugins.base import Plugin, PluginMetadata
from janito.plugins.manager import PluginManager
from janito.plugins.discovery import discover_plugins, list_available_plugins


class TestPlugin(Plugin):
    """Test plugin for unit tests."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="test", version="1.0.0", description="Test plugin", author="Test"
        )

    def get_tools(self):
        return []


def test_plugin_metadata():
    """Test plugin metadata creation."""
    metadata = PluginMetadata(
        name="test", version="1.0.0", description="Test plugin", author="Test"
    )

    assert metadata.name == "test"
    assert metadata.version == "1.0.0"
    assert metadata.description == "Test plugin"
    assert metadata.author == "Test"
    assert metadata.license == "MIT"
    assert metadata.dependencies == []


def test_plugin_manager_initialization():
    """Test plugin manager initialization."""
    manager = PluginManager()
    assert manager.plugins == {}
    assert manager.plugin_configs == {}
    assert isinstance(manager.tools_adapter, object)


def test_plugin_load_unload():
    """Test loading and unloading plugins."""
    manager = PluginManager()

    # Create test plugin
    plugin = TestPlugin()

    # Mock discover_plugins to return our test plugin
    with patch("janito.plugins.manager.discover_plugins", return_value=plugin):
        success = manager.load_plugin("test")
        assert success is True
        assert "test" in manager.plugins

        # Test unloading
        success = manager.unload_plugin("test")
        assert success is True
        assert "test" not in manager.plugins


def test_plugin_load_with_config():
    """Test loading plugin with configuration."""
    manager = PluginManager()

    plugin = TestPlugin()

    with patch("janito.plugins.manager.discover_plugins", return_value=plugin):
        config = {"setting": "value"}
        success = manager.load_plugin("test", config)
        assert success is True
        assert manager.plugin_configs["test"] == config


def test_plugin_discovery():
    """Test plugin discovery."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "test_plugin"
        plugin_dir.mkdir()

        # Create plugin file
        plugin_file = plugin_dir / "plugin.py"
        plugin_file.write_text(
            """
from janito.plugins.base import Plugin, PluginMetadata

class TestPlugin(Plugin):
    def get_metadata(self):
        return PluginMetadata(name="test", version="1.0.0", description="Test", author="Test")
"""
        )

        # Test discovery
        plugin = discover_plugins("test_plugin", [Path(temp_dir)])
        assert plugin is not None
        assert plugin.metadata.name == "test"


def test_list_available_plugins():
    """Test listing available plugins."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create plugin directory
        plugin_dir = Path(temp_dir) / "my_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "__init__.py").write_text("# Plugin init")

        # Create standalone plugin file
        standalone = Path(temp_dir) / "standalone.py"
        standalone.write_text("# Standalone plugin")

        plugins = list_available_plugins([Path(temp_dir)])
        assert "my_plugin" in plugins
        assert "standalone" in plugins


def test_plugin_config_validation():
    """Test plugin configuration validation."""

    class ValidatingPlugin(Plugin):
        def get_metadata(self):
            return PluginMetadata(
                name="validating", version="1.0.0", description="Test", author="Test"
            )

        def validate_config(self, config):
            return "required_key" in config

    manager = PluginManager()
    plugin = ValidatingPlugin()

    with patch("janito.plugins.manager.discover_plugins", return_value=plugin):
        # Valid config
        success = manager.load_plugin("validating", {"required_key": "value"})
        assert success is True

        # Invalid config
        manager.unload_plugin("validating")
        success = manager.load_plugin("validating", {"invalid": "config"})
        assert success is False


if __name__ == "__main__":
    pytest.main([__file__])
