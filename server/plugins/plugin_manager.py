"""
Plugin Manager

Manages plugin processes, lifecycle, and communication.
"""

from __future__ import annotations
import os
import sys
import json
import yaml
import asyncio
import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional, Any, AsyncIterator, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

from server.api.types import FilmetoTask, TaskProgress, TaskResult, ProgressType
from server.api.types import PluginNotFoundError, PluginExecutionError


@dataclass
class ToolInfo:
    """Information about a specific tool supported by a plugin."""
    name: str
    description: str
    parameters: List[Dict[str, Any]]


@dataclass
class PluginInfo:
    """Plugin metadata from plugin.yml"""
    name: str
    version: str
    description: str
    author: str
    # Changed from single tool_type to list of tools
    tools: List[ToolInfo]  # List of supported tools with their configurations
    engine: str
    plugin_path: Path
    main_script: Path
    requirements_file: Optional[Path]
    config: Dict[str, Any]


class PluginProcess:
    """
    Manages a single plugin process and communication.
    """
    
    def __init__(self, plugin_info: PluginInfo):
        """
        Initialize plugin process manager.
        
        Args:
            plugin_info: Plugin metadata
        """
        self.plugin_info = plugin_info
        self.process: Optional[asyncio.subprocess.Process] = None
        self.is_ready = False
        self.heartbeat_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """
        Start the plugin process.
        
        Raises:
            PluginExecutionError: If plugin fails to start
        """
        if self.process and self.process.returncode is None:
            logger.warning(f"Plugin {self.plugin_info.name} is already running")
            return
        
        logger.info(f"Starting plugin: {self.plugin_info.name}")
        
        try:
            # Determine Python executable
            python_exe = sys.executable
            
            # Start process
            self.process = await asyncio.create_subprocess_exec(
                python_exe,
                str(self.plugin_info.main_script),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.plugin_info.plugin_path)
            )
            
            # Wait for ready message
            ready_timeout = self.plugin_info.config.get("startup", {}).get("timeout", 60)
            try:
                ready_msg = await asyncio.wait_for(
                    self._read_message(),
                    timeout=ready_timeout
                )
                
                if ready_msg and ready_msg.get("method") == "ready":
                    self.is_ready = True
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
        while True:
            try:
                message = await self._read_message()
                if message is None:
                    # Process ended or error
                    break
                
                yield message
                
                # Check if this is the final result
                if message.get("result") and "status" in message.get("result", {}):
                    break
                    
            except Exception as e:
                logger.error(f"Error receiving message from plugin: {e}")
                break
    
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
            
            return response and response.get("result", {}).get("status") == "pong"
            
        except:
            return False
    
    async def stop(self):
        """Stop the plugin process"""
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
        self.plugin_infos: Dict[str, PluginInfo] = {}
    
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

                if 'tool_type' in config:
                    tools = [ToolInfo(
                        name=config['tool_type'],
                        description=config.get('description', ''),
                        parameters=config.get('parameters', [])
                    )]
                elif 'tools' in config:
                    tools = []
                    for tool_config in config['tools']:
                        if not isinstance(tool_config, dict) or 'name' not in tool_config:
                            logger.warning(
                                f"Skipping invalid tool entry in plugin {plugin_dir.name}"
                            )
                            continue
                        tools.append(ToolInfo(
                            name=tool_config['name'],
                            description=tool_config.get('description', ''),
                            parameters=tool_config.get('parameters', [])
                        ))
                    if not tools:
                        logger.error(f"Plugin {plugin_dir.name} has no valid tools defined")
                        continue
                else:
                    logger.error(f"Plugin config missing 'tool_type' or 'tools': {plugin_dir.name}")
                    continue

                plugin_info = PluginInfo(
                    name=config['name'],
                    version=config['version'],
                    description=config['description'],
                    author=config.get('author', ''),
                    tools=tools,
                    engine=config['engine'],
                    plugin_path=plugin_dir,
                    main_script=main_script,
                    requirements_file=requirements_file,
                    config=config
                )

                self.plugin_infos[plugin_info.name] = plugin_info

                tool_names = [t.name for t in tools]
                logger.info(f"Discovered plugin: {plugin_info.name} (supports: {', '.join(tool_names)})")

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
        
        Args:
            plugin_name: Name of the plugin
        
        Returns:
            PluginProcess instance
        
        Raises:
            PluginNotFoundError: If plugin not found
            PluginExecutionError: If plugin fails to start
        """
        # Check if plugin is already running
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            # Check if still alive
            if plugin.process and plugin.process.returncode is None:
                return plugin
            else:
                # Process died, remove it
                del self.plugins[plugin_name]
        
        # Get plugin info
        if plugin_name not in self.plugin_infos:
            raise PluginNotFoundError(plugin_name)
        
        plugin_info = self.plugin_infos[plugin_name]
        
        # Create and start plugin process
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
    
    def list_plugins(self) -> list[PluginInfo]:
        """
        List all discovered plugins.
        
        Returns:
            List of PluginInfo objects
        """
        return list(self.plugin_infos.values())
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """
        Get plugin info by name.
        
        Args:
            plugin_name: Name of the plugin
        
        Returns:
            PluginInfo or None if not found
        """
        return self.plugin_infos.get(plugin_name)
    
    def get_plugins_by_tool(self, tool_name: str) -> list[PluginInfo]:
        """
        Get all plugins supporting a specific tool by name.

        Args:
            tool_name: Tool name (e.g., "text2image")

        Returns:
            List of PluginInfo objects
        """
        return [
            info for info in self.plugin_infos.values()
            if any(tool.name == tool_name for tool in info.tools)
        ]
