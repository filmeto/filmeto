"""
Unit tests for server/plugins/plugin_manager.py

Tests plugin manager functionality including:
- AbilityInfo: Ability metadata dataclass
- ServerInfo: Server metadata dataclass
- abilities_from_plugin_yml: Parse abilities from config
- PluginProcess: Plugin process management
- PluginManager: Plugin discovery and management
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from server.plugins.plugin_manager import (
    AbilityInfo,
    ServerInfo,
    abilities_from_plugin_yml,
    PluginProcess,
    PluginManager,
    PluginExecutionError,
)


class TestAbilityInfo:
    """Tests for AbilityInfo dataclass."""

    def test_ability_info_creation(self):
        """AbilityInfo can be created with all fields."""
        ability = AbilityInfo(
            name="text2image",
            description="Generate images from text",
            parameters=[{"name": "prompt", "type": "string"}]
        )
        assert ability.name == "text2image"
        assert ability.description == "Generate images from text"
        assert len(ability.parameters) == 1

    def test_ability_info_empty_parameters(self):
        """AbilityInfo can have empty parameters list."""
        ability = AbilityInfo(
            name="simple",
            description="Simple ability",
            parameters=[]
        )
        assert ability.parameters == []


class TestServerInfo:
    """Tests for ServerInfo dataclass."""

    def test_server_info_creation(self):
        """ServerInfo can be created with all fields."""
        ability = AbilityInfo(name="test", description="desc", parameters=[])
        server = ServerInfo(
            name="TestServer",
            version="1.0.0",
            description="Test server",
            author="test",
            abilities=[ability],
            engine="python",
            plugin_path=Path("/tmp/plugin"),
            main_script=Path("/tmp/plugin/main.py"),
            requirements_file=None,
            config={}
        )
        assert server.name == "TestServer"
        assert server.version == "1.0.0"
        assert len(server.abilities) == 1


class TestAbilitiesFromPluginYml:
    """Tests for abilities_from_plugin_yml function."""

    def test_returns_empty_for_no_abilities(self):
        """abilities_from_plugin_yml returns empty list for no abilities."""
        config = {}
        result = abilities_from_plugin_yml(config)
        assert result == []

    def test_creates_from_single_ability(self):
        """abilities_from_plugin_yml creates from single ability key."""
        config = {
            "ability": "text2image",
            "description": "Image generation",
            "parameters": [{"name": "prompt"}]
        }
        result = abilities_from_plugin_yml(config)
        assert len(result) == 1
        assert result[0].name == "text2image"

    def test_creates_from_abilities_list(self):
        """abilities_from_plugin_yml creates from abilities list."""
        config = {
            "abilities": [
                {"name": "text2image", "description": "Image"},
                {"name": "text2video", "description": "Video"}
            ]
        }
        result = abilities_from_plugin_yml(config)
        assert len(result) == 2

    def test_handles_legacy_tool_type(self):
        """abilities_from_plugin_yml handles legacy tool_type key."""
        config = {
            "tool_type": "legacy_tool",
            "description": "Legacy tool"
        }
        result = abilities_from_plugin_yml(config)
        assert len(result) == 1
        assert result[0].name == "legacy_tool"

    def test_skips_invalid_entries(self):
        """abilities_from_plugin_yml skips invalid ability entries."""
        config = {
            "abilities": [
                {"name": "valid", "description": "Valid"},
                {"description": "Missing name"},  # Invalid
                {"name": "another_valid"}
            ]
        }
        result = abilities_from_plugin_yml(config)
        assert len(result) == 2


class TestPluginExecutionError:
    """Tests for PluginExecutionError exception."""

    def test_error_creation(self):
        """PluginExecutionError can be created."""
        error = PluginExecutionError("Test error")
        assert str(error) == "Test error"


class TestPluginProcessInit:
    """Tests for PluginProcess initialization."""

    def test_init_sets_plugin_info(self):
        """PluginProcess stores plugin_info."""
        server_info = Mock()
        process = PluginProcess(server_info)
        assert process.plugin_info is server_info

    def test_init_sets_default_health_config(self):
        """PluginProcess uses default health config."""
        server_info = Mock()
        server_info.config = {}
        process = PluginProcess(server_info)

        assert process._health_check_interval > 0
        assert process._heartbeat_timeout > 0
        assert process._max_restarts >= 0


class TestPluginProcessIsAlive:
    """Tests for PluginProcess.is_alive property."""

    def test_is_alive_false_when_no_process(self):
        """is_alive returns False when process is None."""
        server_info = Mock()
        server_info.config = {}
        process = PluginProcess(server_info)
        assert process.is_alive is False

    def test_is_alive_true_when_running(self):
        """is_alive returns True when process is running."""
        server_info = Mock()
        server_info.config = {}
        process = PluginProcess(server_info)

        mock_process = Mock()
        mock_process.returncode = None  # Still running
        process.process = mock_process

        assert process.is_alive is True


class TestPluginProcessIsHealthy:
    """Tests for PluginProcess.is_healthy property."""

    def test_is_healthy_false_when_not_alive(self):
        """is_healthy returns False when not alive."""
        server_info = Mock()
        server_info.config = {}
        process = PluginProcess(server_info)
        assert process.is_healthy is False

    def test_is_healthy_true_when_alive_and_ready(self):
        """is_healthy returns True when alive and ready."""
        server_info = Mock()
        server_info.config = {}
        process = PluginProcess(server_info)

        mock_process = Mock()
        mock_process.returncode = None
        process.process = mock_process
        process.is_ready = True
        process._last_heartbeat = 0.0  # No heartbeat yet, assume healthy

        assert process.is_healthy is True


class TestPluginProcessRecordHeartbeat:
    """Tests for PluginProcess.record_heartbeat method."""

    def test_record_heartbeat_updates_timestamp(self):
        """record_heartbeat updates last heartbeat timestamp."""
        import time

        server_info = Mock()
        server_info.config = {}
        process = PluginProcess(server_info)

        process.record_heartbeat()
        assert process._last_heartbeat > 0


class TestPluginManagerInit:
    """Tests for PluginManager initialization."""

    def test_init_with_default_plugins_dir(self):
        """PluginManager uses default plugins directory."""
        manager = PluginManager()
        assert manager.plugins_dir.exists()

    def test_init_with_custom_plugins_dir(self):
        """PluginManager uses custom plugins directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PluginManager(tmpdir)
            assert str(manager.plugins_dir) == tmpdir

    def test_init_creates_empty_plugins_dict(self):
        """PluginManager creates empty plugins dict."""
        manager = PluginManager()
        assert manager.plugins == {}

    def test_init_creates_empty_plugin_infos_dict(self):
        """PluginManager creates empty plugin_infos dict."""
        manager = PluginManager()
        assert manager.plugin_infos == {}


class TestPluginManagerDiscoverPlugins:
    """Tests for PluginManager.discover_plugins method."""

    def test_discover_plugins_handles_missing_dir(self):
        """discover_plugins handles non-existent directory."""
        manager = PluginManager("/nonexistent/path")
        manager.discover_plugins()
        assert manager.plugin_infos == {}

    def test_discover_plugins_skips_underscore_dirs(self):
        """discover_plugins skips directories starting with underscore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create underscore dir
            underscore_dir = Path(tmpdir) / "_hidden"
            underscore_dir.mkdir()

            manager = PluginManager(tmpdir)
            manager.discover_plugins()

            assert manager.plugin_infos == {}


class TestPluginManagerIsVersionCompatible:
    """Tests for PluginManager._is_version_compatible static method."""

    def test_valid_semver_returns_true(self):
        """_is_version_compatible returns True for valid semver."""
        assert PluginManager._is_version_compatible("1.0.0") is True
        assert PluginManager._is_version_compatible("2.3.4") is True

    def test_invalid_format_returns_false(self):
        """_is_version_compatible returns False for invalid format."""
        assert PluginManager._is_version_compatible("1.0") is False
        assert PluginManager._is_version_compatible("v1.0.0") is False
        assert PluginManager._is_version_compatible("") is False

    def test_non_numeric_parts_returns_false(self):
        """_is_version_compatible returns False for non-numeric parts."""
        assert PluginManager._is_version_compatible("1.a.0") is False


class TestPluginManagerListPlugins:
    """Tests for PluginManager.list_plugins method."""

    def test_list_plugins_returns_empty_list(self):
        """list_plugins returns empty list when no plugins."""
        manager = PluginManager()
        result = manager.list_plugins()
        assert result == []

    def test_list_plugins_returns_plugin_infos(self):
        """list_plugins returns list of ServerInfo."""
        manager = PluginManager()
        mock_info = Mock()
        manager.plugin_infos = {"test": mock_info}

        result = manager.list_plugins()
        assert mock_info in result


class TestPluginManagerGetPluginInfo:
    """Tests for PluginManager.get_plugin_info method."""

    def test_get_plugin_info_returns_info(self):
        """get_plugin_info returns ServerInfo for existing plugin."""
        manager = PluginManager()
        mock_info = Mock()
        manager.plugin_infos = {"test_server": mock_info}

        result = manager.get_plugin_info("test_server")
        assert result is mock_info

    def test_get_plugin_info_returns_none_missing(self):
        """get_plugin_info returns None for missing plugin."""
        manager = PluginManager()
        result = manager.get_plugin_info("nonexistent")
        assert result is None


class TestPluginManagerGetServersByAbility:
    """Tests for PluginManager.get_servers_by_ability method."""

    def test_get_servers_by_ability_returns_matching(self):
        """get_servers_by_ability returns servers with matching ability."""
        manager = PluginManager()

        ability1 = AbilityInfo(name="text2image", description="", parameters=[])
        ability2 = AbilityInfo(name="text2video", description="", parameters=[])

        server1 = Mock()
        server1.abilities = [ability1]
        server2 = Mock()
        server2.abilities = [ability2]

        manager.plugin_infos = {"s1": server1, "s2": server2}

        result = manager.get_servers_by_ability("text2image")
        assert server1 in result
        assert server2 not in result

    def test_get_servers_by_ability_empty_when_none(self):
        """get_servers_by_ability returns empty list when no match."""
        manager = PluginManager()
        manager.plugin_infos = {}

        result = manager.get_servers_by_ability("nonexistent")
        assert result == []


class TestPluginManagerStopAllPlugins:
    """Tests for PluginManager.stop_all_plugins async method."""

    @pytest.mark.asyncio
    async def test_stop_all_plugins_stops_all(self):
        """stop_all_plugins stops all running plugins."""
        manager = PluginManager()

        mock_plugin1 = Mock()
        mock_plugin1.stop = AsyncMock()
        mock_plugin2 = Mock()
        mock_plugin2.stop = AsyncMock()

        manager.plugins = {"p1": mock_plugin1, "p2": mock_plugin2}

        await manager.stop_all_plugins()

        mock_plugin1.stop.assert_called_once()
        mock_plugin2.stop.assert_called_once()
        assert manager.plugins == {}