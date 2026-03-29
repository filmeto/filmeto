"""
Plugin Manager

Manages plugin processes, lifecycle, and communication.
"""

from __future__ import annotations
import os
import sys
import json
import time
import yaml
import asyncio
import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional, Any, AsyncIterator, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_DEFAULT_HEALTH_CHECK_INTERVAL = 30   # seconds between checks
_DEFAULT_HEARTBEAT_TIMEOUT = 90       # seconds before declaring unhealthy
_DEFAULT_MAX_RESTARTS = 3

from server.api.types import FilmetoTask, TaskProgress, TaskResult, ProgressType
from server.api.types import ServerNotFoundError, ServerExecutionError


class PluginExecutionError(Exception):
    """Exception raised when plugin execution fails."""
    pass


@dataclass
class CapabilityInfo:
    """Information about a specific capability supported by a server."""
    name: str
    description: str
    parameters: List[Dict[str, Any]]


@dataclass
class ServerInfo:
    """Server metadata from plugin.yml"""
    name: str
    version: str
    description: str
    author: str
    # List of supported capabilities with their configurations
    capabilities: List[CapabilityInfo]
    engine: str
    plugin_path: Path
    main_script: Path
    requirements_file: Optional[Path]
    config: Dict[str, Any]


def capabilities_from_plugin_yml(
    config: Dict[str, Any], plugin_dir_name: str = ""
) -> List[CapabilityInfo]:
    """
    Build CapabilityInfo list from plugin.yml.

    Preferred keys: ``ability`` (single string) and ``abilities`` (list of entries).
    Legacy: ``tool_type`` and ``tools`` (same shapes).
    """
    single = config.get("ability") or config.get("tool_type")
    if single:
        return [
            CapabilityInfo(
                name=str(single),
                description=config.get("description", ""),
                parameters=config.get("parameters", []),
            )
        ]

    entries = config.get("abilities") or config.get("tools")
    if not entries:
        return []

    capabilities: List[CapabilityInfo] = []
    for cap_config in entries:
        if not isinstance(cap_config, dict) or "name" not in cap_config:
            logger.warning(
                "Skipping invalid ability entry in server %s",
                plugin_dir_name or "unknown",
            )
            continue
        capabilities.append(
            CapabilityInfo(
                name=cap_config["name"],
                description=cap_config.get("description", ""),
                parameters=cap_config.get("parameters", []),
            )
        )
    return capabilities


class PluginProcess:
    """
    Manages a single plugin process and communication.
    """
    
    def __init__(self, plugin_info: ServerInfo):
        self.plugin_info = plugin_info
        self.process: Optional[asyncio.subprocess.Process] = None
        self.is_ready = False

        # Health check state
        startup_cfg = plugin_info.config.get("startup", {})
        self._health_check_interval: int = startup_cfg.get(
            "health_check_interval", _DEFAULT_HEALTH_CHECK_INTERVAL
        )
        self._heartbeat_timeout: int = startup_cfg.get(
            "heartbeat_timeout", _DEFAULT_HEARTBEAT_TIMEOUT
        )
        self._max_restarts: int = startup_cfg.get(
            "max_restarts", _DEFAULT_MAX_RESTARTS
        )

        self._last_heartbeat: float = 0.0
        self._restart_count: int = 0
        self._is_executing: bool = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._on_restart_callback = None
    
    @property
    def is_alive(self) -> bool:
        """True if the process is running."""
        return (
            self.process is not None
            and self.process.returncode is None
        )

    @property
    def is_healthy(self) -> bool:
        """True if alive and heartbeat is recent enough."""
        if not self.is_alive or not self.is_ready:
            return False
        if self._last_heartbeat == 0.0:
            return True
        return (time.time() - self._last_heartbeat) < self._heartbeat_timeout

    def record_heartbeat(self):
        """Record that a heartbeat was received from the plugin."""
        self._last_heartbeat = time.time()

    async def start(self):
        """
        Start the plugin process.
        
        Raises:
            PluginExecutionError: If plugin fails to start
        """
        if self.is_alive:
            logger.warning(f"Plugin {self.plugin_info.name} is already running")
            return
        
        logger.info(f"Starting plugin: {self.plugin_info.name}")
        
        try:
            python_exe = sys.executable
            
            self.process = await asyncio.create_subprocess_exec(
                python_exe,
                str(self.plugin_info.main_script),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.plugin_info.plugin_path)
            )
            
            ready_timeout = self.plugin_info.config.get("startup", {}).get("timeout", 60)
            try:
                ready_msg = await asyncio.wait_for(
                    self._read_message(),
                    timeout=ready_timeout
                )
                
                if ready_msg and ready_msg.get("method") == "ready":
                    self.is_ready = True
                    self.record_heartbeat()
                    logger.info(f"Plugin {self.plugin_info.name} is ready")
                else:
                    raise PluginExecutionError(
                        f"Plugin {self.plugin_info.name} did not send ready message",
                        {"plugin": self.plugin_info.name}
                    )
                    
            except asyncio.TimeoutError:
                await self.stop()
                raise PluginExecutionError(
                    f"Plugin {self.plugin_info.name} startup timeout",
                    {"plugin": self.plugin_info.name, "timeout": ready_timeout}
                )

            # Launch the background health check
            health_check_enabled = self.plugin_info.config.get(
                "startup", {}
            ).get("health_check", False)
            if health_check_enabled:
                self._health_check_task = asyncio.create_task(
                    self._health_check_loop()
                )
            
        except PluginExecutionError:
            raise
        except Exception as e:
            await self.stop()
            raise PluginExecutionError(
                f"Failed to start plugin {self.plugin_info.name}: {str(e)}",
                {"plugin": self.plugin_info.name, "error": str(e)}
            )
    
    async def send_task(self, task: FilmetoTask):
        """
        Send task to plugin.
        
        Args:
            task: Task to execute
        """
        if not self.is_ready:
            raise PluginExecutionError(
                f"Plugin {self.plugin_info.name} is not ready",
                {"plugin": self.plugin_info.name}
            )
        
        self._is_executing = True

        request = {
            "jsonrpc": "2.0",
            "method": "execute_task",
            "params": task.to_dict(),
            "id": 1
        }
        
        await self._write_message(request)
    
    async def receive_messages(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Receive messages from plugin.
        
        Yields:
            Message dictionaries (progress, result, heartbeat)
        """
        try:
            while True:
                try:
                    message = await self._read_message()
                    if message is None:
                        break

                    if message.get("method") == "heartbeat":
                        self.record_heartbeat()

                    yield message
                    
                    if message.get("result") and "status" in message.get("result", {}):
                        break
                        
                except Exception as e:
                    logger.error(f"Error receiving message from plugin: {e}")
                    break
        finally:
            self._is_executing = False
    
    async def ping(self) -> bool:
        """
        Ping the plugin to check if it's alive.
        
        Returns:
            True if plugin responds, False otherwise
        """
        if not self.is_ready:
            return False
        
        try:
            request = {
                "jsonrpc": "2.0",
                "method": "ping",
                "params": {},
                "id": 999
            }
            
            await self._write_message(request)
            
            # Wait for response with timeout
            response = await asyncio.wait_for(self._read_message(), timeout=5.0)
            
            alive = response and response.get("result", {}).get("status") == "pong"
            if alive:
                self.record_heartbeat()
            return alive
            
        except Exception:
            return False
    
    async def _health_check_loop(self):
        """Periodically verify the plugin is alive. Only pings when idle."""
        name = self.plugin_info.name
        try:
            while self.is_alive:
                await asyncio.sleep(self._health_check_interval)

                if not self.is_alive:
                    break

                # During task execution, rely on heartbeat messages from the
                # plugin instead of sending a ping (which would conflict with
                # the task message stream on stdout).
                if self._is_executing:
                    if self._last_heartbeat and (
                        time.time() - self._last_heartbeat > self._heartbeat_timeout
                    ):
                        logger.warning(
                            f"Plugin {name} heartbeat timeout during execution"
                        )
                        await self._restart()
                    continue

                # Idle: actively ping.
                if not await self.ping():
                    logger.warning(f"Plugin {name} failed ping check")
                    await self._restart()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Health check loop error for {name}: {e}")

    async def _restart(self):
        """Stop and restart the plugin process with a restart budget."""
        name = self.plugin_info.name
        if self._restart_count >= self._max_restarts:
            logger.error(
                f"Plugin {name} exceeded max restarts ({self._max_restarts}), "
                "giving up"
            )
            await self.stop()
            return

        self._restart_count += 1
        logger.info(
            f"Restarting plugin {name} "
            f"(attempt {self._restart_count}/{self._max_restarts})"
        )

        await self.stop()
        try:
            await self.start()
            if self._on_restart_callback:
                self._on_restart_callback(self)
        except PluginExecutionError as e:
            logger.error(f"Failed to restart plugin {name}: {e}")

    async def stop(self):
        """Stop the plugin process and cancel health check."""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

        if self.process:
            try:
                if self.process.returncode is None:
                    self.process.terminate()
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            except Exception as e:
                logger.error(f"Error stopping plugin: {e}")
            
            self.process = None
        
        self.is_ready = False
        self._is_executing = False
    
    async def _write_message(self, message: Dict[str, Any]):
        """Write JSON message to plugin stdin"""
        if not self.process or not self.process.stdin:
            raise PluginExecutionError(
                f"Plugin {self.plugin_info.name} stdin not available",
                {"plugin": self.plugin_info.name}
            )
        
        try:
            json_str = json.dumps(message) + '\n'
            self.process.stdin.write(json_str.encode())
            await self.process.stdin.drain()
        except Exception as e:
            raise PluginExecutionError(
                f"Failed to write to plugin {self.plugin_info.name}: {str(e)}",
                {"plugin": self.plugin_info.name, "error": str(e)}
            )
    
    async def _read_message(self) -> Optional[Dict[str, Any]]:
        """Read JSON message from plugin stdout"""
        if not self.process or not self.process.stdout:
            return None
        
        try:
            line = await self.process.stdout.readline()
            if not line:
                return None
            
            return json.loads(line.decode().strip())
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from plugin: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading from plugin: {e}")
            return None
    
    def __repr__(self) -> str:
        return f"PluginProcess({self.plugin_info.name}, ready={self.is_ready})"


class PluginManager:
    """
    Manages multiple plugin processes.
    """
    
    def __init__(self, plugins_dir: Optional[str] = None):
        """
        Initialize plugin manager.
        
        Args:
            plugins_dir: Directory containing plugins (default: server/plugins/)
        """
        if plugins_dir:
            self.plugins_dir = Path(plugins_dir)
        else:
            # Default to server/plugins directory
            self.plugins_dir = Path(__file__).parent
        
        self.plugins: Dict[str, PluginProcess] = {}
        self.plugin_infos: Dict[str, ServerInfo] = {}
    
    def discover_plugins(self):
        """
        Discover available plugins in the plugins directory.
        """
        logger.info(f"Discovering plugins in: {self.plugins_dir}")

        if not self.plugins_dir.exists():
            logger.error(f"Plugins directory not found: {self.plugins_dir}")
            return

        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith('_'):
                continue

            config_file = plugin_dir / "plugin.yml"
            if not config_file.exists():
                logger.warning(f"Plugin directory missing plugin.yml: {plugin_dir.name}")
                continue

            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)

                if not isinstance(config, dict):
                    logger.error(f"Invalid plugin config (not a mapping): {plugin_dir.name}")
                    continue

                required_fields = ['name', 'version', 'description', 'engine']
                missing = [f for f in required_fields if f not in config]
                if missing:
                    logger.error(f"Plugin {plugin_dir.name} missing required fields: {missing}")
                    continue

                if not self._is_version_compatible(config['version']):
                    logger.warning(
                        f"Plugin {config['name']} version {config['version']} may be incompatible"
                    )

                main_script = plugin_dir / "main.py"
                if not main_script.exists():
                    logger.error(f"Plugin main.py not found: {plugin_dir.name}")
                    continue

                requirements_file = plugin_dir / "requirements.txt"
                if not requirements_file.exists():
                    requirements_file = None

                capabilities = capabilities_from_plugin_yml(config, plugin_dir.name)
                if not capabilities:
                    logger.error(
                        f"Server {plugin_dir.name} missing ability definitions: "
                        f"expected 'ability' / 'abilities' (or legacy 'tool_type' / 'tools')"
                    )
                    continue

                server_info = ServerInfo(
                    name=config['name'],
                    version=config['version'],
                    description=config['description'],
                    author=config.get('author', ''),
                    capabilities=capabilities,
                    engine=config['engine'],
                    plugin_path=plugin_dir,
                    main_script=main_script,
                    requirements_file=requirements_file,
                    config=config
                )

                self.plugin_infos[server_info.name] = server_info

                cap_names = [c.name for c in capabilities]
                logger.info(f"Discovered server: {server_info.name} (capabilities: {', '.join(cap_names)})")

            except yaml.YAMLError as e:
                logger.error(f"Invalid YAML in plugin {plugin_dir.name}: {e}")
            except Exception as e:
                logger.error(f"Failed to load plugin config {plugin_dir.name}: {e}")

    @staticmethod
    def _is_version_compatible(version: str) -> bool:
        """Check if a plugin version string is a recognized semver format."""
        try:
            parts = version.split('.')
            if len(parts) != 3:
                return False
            int(parts[0]), int(parts[1]), int(parts[2])
            return True
        except (ValueError, AttributeError):
            return False
    
    async def get_plugin(self, plugin_name: str) -> PluginProcess:
        """
        Get or start a plugin process.

        If the cached process has died or is unhealthy it is recycled
        transparently before being returned.
        
        Args:
            plugin_name: Name of the plugin
        
        Returns:
            PluginProcess instance
        
        Raises:
            PluginNotFoundError: If plugin not found
            PluginExecutionError: If plugin fails to start
        """
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            if plugin.is_alive and plugin.is_healthy:
                return plugin
            # Process died or is unhealthy — clean up and re-create.
            logger.warning(
                f"Plugin {plugin_name} is not healthy "
                f"(alive={plugin.is_alive}, healthy={plugin.is_healthy}), "
                "recycling"
            )
            await plugin.stop()
            del self.plugins[plugin_name]
        
        if plugin_name not in self.plugin_infos:
            raise PluginNotFoundError(plugin_name)
        
        plugin_info = self.plugin_infos[plugin_name]
        
        plugin = PluginProcess(plugin_info)
        await plugin.start()
        
        self.plugins[plugin_name] = plugin
        return plugin
    
    async def stop_plugin(self, plugin_name: str):
        """
        Stop a plugin process.
        
        Args:
            plugin_name: Name of the plugin
        """
        if plugin_name in self.plugins:
            await self.plugins[plugin_name].stop()
            del self.plugins[plugin_name]
            logger.info(f"Stopped plugin: {plugin_name}")
    
    async def stop_all_plugins(self):
        """Stop all running plugins"""
        for plugin_name in list(self.plugins.keys()):
            await self.stop_plugin(plugin_name)
    
    def list_plugins(self) -> list[ServerInfo]:
        """
        List all discovered plugins.
        
        Returns:
            List of ServerInfo objects
        """
        return list(self.plugin_infos.values())
    
    def get_plugin_info(self, plugin_name: str) -> Optional[ServerInfo]:
        """
        Get plugin info by name.
        
        Args:
            plugin_name: Name of the plugin
        
        Returns:
            ServerInfo or None if not found
        """
        return self.plugin_infos.get(plugin_name)
    
    def get_servers_by_capability(self, capability_name: str) -> list[ServerInfo]:
        """
        Get all servers supporting a specific capability by name.

        Args:
            capability_name: Capability name (e.g., "text2image")

        Returns:
            List of ServerInfo objects
        """
        return [
            info for info in self.plugin_infos.values()
            if any(cap.name == capability_name for cap in info.capabilities)
        ]
