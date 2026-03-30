"""
Server Manager Module

Manages server instances and routing for task execution.
Servers represent different AIGC service providers (ComfyUI, Bailian, Local, etc.)
that can generate images, videos, audio, and other storyboard materials.
"""

import os
import time
import threading
import yaml
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent

from server.api.types import FilmetoTask, TaskProgress, TaskResult, RetryPolicy
from server.plugins.plugin_manager import PluginManager, ServerInfo
from server.plugins.plugin_ui_loader import PluginUILoader

logger = logging.getLogger(__name__)

_RELOAD_DEBOUNCE_SECONDS = 1.0


class _ConfigWatcher(FileSystemEventHandler):
    """Watches the servers directory for config changes and triggers reloads."""

    def __init__(self, server_manager: 'ServerManager'):
        super().__init__()
        self._server_manager = server_manager
        self._pending: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None

    # -- watchdog callbacks (called on observer thread) ---------------------

    def on_modified(self, event):
        if not isinstance(event, FileModifiedEvent) or event.is_directory:
            return
        self._schedule_reload(event.src_path)

    def on_created(self, event):
        if not isinstance(event, FileCreatedEvent) or event.is_directory:
            return
        self._schedule_reload(event.src_path)

    def on_deleted(self, event):
        if not isinstance(event, FileDeletedEvent) or event.is_directory:
            return
        self._schedule_reload(event.src_path)

    # -- internal ----------------------------------------------------------

    def _schedule_reload(self, path: str):
        """Debounce rapid file-system events into a single reload."""
        p = Path(path)
        if p.name not in ("server.yml", "server_router.yml"):
            return

        with self._lock:
            self._pending[path] = time.time()
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(
                _RELOAD_DEBOUNCE_SECONDS, self._flush
            )
            self._timer.daemon = True
            self._timer.start()

    def _flush(self):
        with self._lock:
            paths = dict(self._pending)
            self._pending.clear()
            self._timer = None

        for path_str in paths:
            p = Path(path_str)
            if p.name == "server_router.yml":
                self._server_manager.reload_routing_rules()
            elif p.name == "server.yml":
                server_name = p.parent.name
                if p.exists():
                    self._server_manager.reload_server(server_name)
                else:
                    self._server_manager._handle_server_config_deleted(server_name)

    def cancel(self):
        """Cancel any pending timer."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None


@dataclass
class ServerConfig:
    """
    Configuration for a server instance.
    
    Attributes:
        name: Server name (must be unique)
        server_type: Type of server (comfyui, bailian, local, filmeto, etc.)
        description: Human-readable description
        enabled: Whether the server is enabled
        plugin_name: Associated plugin name for task execution
        endpoint: Optional endpoint URL for remote services
        api_key: Optional API key for authentication
        parameters: Additional server-specific parameters
        metadata: Additional metadata
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    name: str
    server_type: str
    plugin_name: str
    description: str = ""
    enabled: bool = True
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YML serialization"""
        return {
            "name": self.name,
            "server_type": self.server_type,
            "plugin_name": self.plugin_name,
            "description": self.description,
            "enabled": self.enabled,
            "endpoint": self.endpoint,
            "api_key": self.api_key,
            "parameters": self.parameters,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServerConfig':
        """Create from dictionary loaded from YML"""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
        
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now()
        
        return cls(
            name=data["name"],
            server_type=data["server_type"],
            plugin_name=data["plugin_name"],
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            endpoint=data.get("endpoint"),
            api_key=data.get("api_key"),
            parameters=data.get("parameters", {}),
            metadata=data.get("metadata", {}),
            created_at=created_at,
            updated_at=updated_at,
        )
    
    def save_to_file(self, file_path: str):
        """Save configuration to YML file"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.to_dict(), f, allow_unicode=True, sort_keys=False)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'ServerConfig':
        """Load configuration from YML file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)


@dataclass
class RoutingRule:
    """
    Routing rule for task distribution.
    
    Attributes:
        name: Rule name
        priority: Priority (higher = execute first)
        conditions: Conditions for matching (tool_name, parameters, etc.)
        server_name: Target server name
        fallback_servers: List of fallback server names if primary fails
        enabled: Whether the rule is enabled
    """
    name: str
    server_name: str
    priority: int = 0
    conditions: Dict[str, Any] = field(default_factory=dict)
    fallback_servers: List[str] = field(default_factory=list)
    enabled: bool = True
    
    def matches(self, task: FilmetoTask) -> bool:
        """Check if this rule matches the given task"""
        if not self.enabled:
            return False

        cond_ability = self.conditions.get("ability")
        if cond_ability is None and "capability" in self.conditions:
            cond_ability = self.conditions["capability"]
        if cond_ability is not None:
            if isinstance(cond_ability, list):
                if task.ability.value not in cond_ability:
                    return False
            elif task.ability.value != cond_ability:
                return False

        # Check server_name condition
        if "server_name" in self.conditions:
            if task.server_name != self.conditions["server_name"]:
                return False

        # Check custom parameters
        if "parameters" in self.conditions:
            for key, value in self.conditions["parameters"].items():
                if task.parameters.get(key) != value:
                    return False

        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "priority": self.priority,
            "conditions": self.conditions,
            "server_name": self.server_name,
            "fallback_servers": self.fallback_servers,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RoutingRule':
        """Create from dictionary"""
        return cls(
            name=data["name"],
            server_name=data["server_name"],
            priority=data.get("priority", 0),
            conditions=data.get("conditions", {}),
            fallback_servers=data.get("fallback_servers", []),
            enabled=data.get("enabled", True),
        )


class Server:
    """
    Server instance that manages plugin execution.
    
    A server represents a connection to an AIGC service provider
    and provides methods to execute tasks through its associated plugin.
    """
    
    def __init__(self, config: ServerConfig, plugin_manager: PluginManager, workspace_path: Optional[Path] = None):
        """
        Initialize server instance.
        
        Args:
            config: Server configuration
            plugin_manager: Plugin manager for task execution
            workspace_path: Optional workspace path for workflow loading
        """
        self.config = config
        self.plugin_manager = plugin_manager
        self.workspace_path = workspace_path
        self._plugin_info: Optional[ServerInfo] = None
    
    @property
    def name(self) -> str:
        """Get server name"""
        return self.config.name
    
    @property
    def server_type(self) -> str:
        """Get server type"""
        return self.config.server_type
    
    @property
    def is_enabled(self) -> bool:
        """Check if server is enabled"""
        return self.config.enabled
    
    def get_plugin_info(self) -> Optional[ServerInfo]:
        """Get associated plugin information"""
        if self._plugin_info is None:
            self._plugin_info = self.plugin_manager.get_plugin_info(self.config.plugin_name)
        return self._plugin_info

    def get_retry_policy(self) -> RetryPolicy:
        """Build a RetryPolicy from the plugin's ``execution`` config section.

        Falls back to server-level ``parameters.retry`` if present, otherwise
        uses the plugin.yml ``execution`` block, otherwise defaults.
        """
        server_retry = self.config.parameters.get("retry")
        if isinstance(server_retry, dict):
            return RetryPolicy.from_dict(server_retry)

        plugin_info = self.get_plugin_info()
        if plugin_info is not None:
            exec_cfg = plugin_info.config.get("execution", {})
            if exec_cfg:
                return RetryPolicy.from_dict(exec_cfg)

        return RetryPolicy()

    async def execute_task(
        self,
        task: FilmetoTask
    ) -> Union[TaskProgress, TaskResult]:
        """
        Execute a task through the server's plugin.
        
        Args:
            task: Task to execute
            
        Yields:
            TaskProgress: Progress updates
            TaskResult: Final result
        """
        if not self.is_enabled:
            raise Exception(f"Server '{self.name}' is disabled")
        
        # Get plugin
        plugin = await self.plugin_manager.get_plugin(self.config.plugin_name)
        
        # Inject server-specific parameters
        if self.config.parameters:
            task.metadata["server_config"] = self.config.parameters
        
        # Inject workspace_path and server_name for workflow loading
        if self.workspace_path:
            task.metadata["workspace_path"] = str(self.workspace_path)
            task.metadata["server_name"] = self.config.name
        
        # Send task to plugin
        await plugin.send_task(task)
        
        # Receive and yield messages
        async for message in plugin.receive_messages():
            yield message
    
    def __repr__(self) -> str:
        return f"Server(name={self.name}, type={self.server_type}, enabled={self.is_enabled})"


class ServerManager:
    """
    Manages server instances and task routing.

    Provides CRUD operations for servers and routes tasks to appropriate
    servers based on routing rules.
    """
    _instance = None
    _initialized = False
    _workspace_path = None
    _defer_plugin_discovery = False
    _lock = threading.Lock()

    def __new__(cls, workspace_path: str, plugin_manager: Optional[PluginManager] = None, defer_plugin_discovery: bool = False):
        """
        Create or return the singleton instance of ServerManager (thread-safe).
        """
        cls._defer_plugin_discovery = defer_plugin_discovery
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ServerManager, cls).__new__(cls)
        return cls._instance

    def __init__(
        self,
        workspace_path: str,
        plugin_manager: Optional[PluginManager] = None,
        defer_plugin_discovery: bool = False
    ):
        """
        Initialize server manager (only once).

        Args:
            workspace_path: Path to workspace root
            plugin_manager: Plugin manager instance (creates new if None)
            defer_plugin_discovery: If True, skip plugin discovery during init (do it later)
        """
        # Get defer flag from class variable (set by __new__)
        defer_plugin_discovery = self.__class__._defer_plugin_discovery
        
        # Check if we need to reinitialize because workspace path has changed
        if self._initialized and str(self._workspace_path) != str(workspace_path):
            logger.warning(f"⚠️ ServerManager workspace path changed from {self._workspace_path} to {workspace_path}")
            # For singleton, we'll stick with the first workspace path
            # This might need to be handled differently based on requirements
            return

        # Only initialize once
        if self._initialized:
            return

        self.workspace_path = Path(workspace_path)
        self._workspace_path = self.workspace_path  # Store for comparison later
        self.servers_dir = self.workspace_path / "servers"
        self.router_config_path = self.servers_dir / "server_router.yml"

        # Initialize plugin manager (for subprocess execution)
        if plugin_manager is None:
            self.plugin_manager = PluginManager()
            if not defer_plugin_discovery:
                self.plugin_manager.discover_plugins()
        else:
            self.plugin_manager = plugin_manager

        # Initialize plugin UI loader (for UI component loading)
        # Note: plugins_dir might not exist if discovery is deferred
        if hasattr(self.plugin_manager, 'plugins_dir') and self.plugin_manager.plugins_dir:
            self.plugin_ui_loader = PluginUILoader(self.plugin_manager.plugins_dir)
        else:
            # Will be initialized after plugin discovery
            self.plugin_ui_loader = None

        # Server instances
        self.servers: Dict[str, Server] = {}

        # Routing rules
        self.routing_rules: List[RoutingRule] = []

        # Initialize
        self._ensure_directories()
        self.cleanup_old_configs()  # Clean up old configurations first
        self._init_default_servers()
        self._load_servers()
        self._load_routing_rules()

        # Store flag for deferred discovery
        self._plugin_discovery_deferred = defer_plugin_discovery

        # Config watcher (started lazily via start_config_watcher)
        self._config_observer: Optional[Observer] = None
        self._config_watcher: Optional[_ConfigWatcher] = None

        # Mark as initialized
        self._initialized = True

    def _complete_plugin_discovery(self):
        """Complete plugin discovery if it was deferred during initialization"""
        if self._plugin_discovery_deferred:
            self.plugin_manager.discover_plugins()
            # Initialize plugin UI loader now that plugins are discovered
            if hasattr(self.plugin_manager, 'plugins_dir') and self.plugin_manager.plugins_dir:
                self.plugin_ui_loader = PluginUILoader(self.plugin_manager.plugins_dir)
            self._plugin_discovery_deferred = False
    
    @classmethod
    def get_instance(cls) -> Optional['ServerManager']:
        """
        Get the singleton instance of ServerManager.

        Returns:
            ServerManager instance if it exists, None otherwise
        """
        return cls._instance
    
    def _ensure_directories(self):
        """Ensure server directories exist"""
        self.servers_dir.mkdir(parents=True, exist_ok=True)
    
    def _init_default_servers(self):
        """Initialize default servers (local and filmeto) if they don't exist"""
        # Default local server
        local_server_dir = self.servers_dir / "local"
        local_config_path = local_server_dir / "server.yml"

        if not local_config_path.exists():
            local_config = ServerConfig(
                name="local",
                server_type="local",
                plugin_name="Local Server",  # Default local plugin
                description="Local AIGC service running on this machine",
                enabled=True,
                endpoint="http://localhost:8188",
            )
            local_config.save_to_file(str(local_config_path))
            logger.info(f"✅ Created default server: local")

        # Default filmeto server
        filmeto_server_dir = self.servers_dir / "filmeto"
        filmeto_config_path = filmeto_server_dir / "server.yml"

        if not filmeto_config_path.exists():
            filmeto_config = ServerConfig(
                name="filmeto",
                server_type="filmeto",
                plugin_name="Filmeto Server",  # Default filmeto plugin
                description="Filmeto built-in AIGC service",
                enabled=True,
            )
            filmeto_config.save_to_file(str(filmeto_config_path))
            logger.info(f"✅ Created default server: filmeto")

        # Default routing rules
        if not self.router_config_path.exists():
            default_rules = {
                "routing_rules": [
                    {
                        "name": "default_local",
                        "priority": 0,
                        "conditions": {},
                        "server_name": "local",
                        "fallback_servers": ["filmeto"],
                        "enabled": True,
                    }
                ]
            }
            with open(self.router_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_rules, f, allow_unicode=True, sort_keys=False)
            logger.info(f"✅ Created default routing rules")

    def cleanup_old_configs(self):
        """Clean up any old or invalid plugin configurations in the workspace"""
        if not self.servers_dir.exists():
            return

        # Get list of all plugin directories
        all_plugin_dirs = [d for d in self.servers_dir.iterdir() if d.is_dir()]

        for plugin_dir in all_plugin_dirs:
            # Skip default servers
            if plugin_dir.name in ["local", "filmeto"]:
                continue

            config_path = plugin_dir / "server.yml"
            if config_path.exists():
                try:
                    # Try to load the config
                    config = ServerConfig.load_from_file(str(config_path))

                    # If we can load it, it should be valid
                    logger.info(f"✅ Valid config found for: {config.name}")
                except Exception as e:
                    # If there's an error loading the config, delete the entire directory
                    import shutil
                    logger.error(f"❌ Invalid config in {plugin_dir.name}: {e} - removing")
                    shutil.rmtree(plugin_dir)
                    logger.info(f"🗑️ Removed invalid server config: {plugin_dir.name}")
    
    def _load_servers(self):
        """Load all server configurations"""
        if not self.servers_dir.exists():
            return
        
        for server_dir in self.servers_dir.iterdir():
            if not server_dir.is_dir():
                continue

            config_path = server_dir / "server.yml"
            if not config_path.exists():
                continue

            try:
                config = ServerConfig.load_from_file(str(config_path))
                server = Server(config, self.plugin_manager, self.workspace_path)
                self.servers[config.name] = server
                logger.info(f"✅ Loaded server: {config.name} ({config.server_type})")
            except Exception as e:
                logger.error(f"❌ Failed to load server from {server_dir}: {e}")
    
    def _load_routing_rules(self):
        """Load routing rules from configuration"""
        if not self.router_config_path.exists():
            return
        
        try:
            with open(self.router_config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            rules_data = data.get("routing_rules", [])
            self.routing_rules = [RoutingRule.from_dict(rule) for rule in rules_data]
            
            # Sort by priority (higher first)
            self.routing_rules.sort(key=lambda r: r.priority, reverse=True)
            
            logger.info(f"✅ Loaded {len(self.routing_rules)} routing rules")
        except Exception as e:
            logger.error(f"❌ Failed to load routing rules: {e}")
    
    def _save_routing_rules(self):
        """Save routing rules to configuration"""
        rules_data = {
            "routing_rules": [rule.to_dict() for rule in self.routing_rules]
        }
        with open(self.router_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(rules_data, f, allow_unicode=True, sort_keys=False)
    
    # CRUD Operations
    
    def add_server(self, config: ServerConfig) -> Server:
        """
        Add a new server.
        
        Args:
            config: Server configuration
            
        Returns:
            Created server instance
            
        Raises:
            ValueError: If server name already exists
        """
        if config.name in self.servers:
            raise ValueError(f"Server '{config.name}' already exists")
        
        # Verify plugin exists
        plugin_info = self.plugin_manager.get_plugin_info(config.plugin_name)
        if plugin_info is None:
            raise ValueError(f"Plugin '{config.plugin_name}' not found")
        
        # Save configuration
        server_dir = self.servers_dir / config.name
        config_path = server_dir / "server.yml"
        config.save_to_file(str(config_path))
        
        # Create server instance
        server = Server(config, self.plugin_manager, self.workspace_path)
        self.servers[config.name] = server
        
        logger.info(f"✅ Added server: {config.name}")
        return server
    
    def get_server(self, name: str) -> Optional[Server]:
        """
        Get server by name.
        
        Args:
            name: Server name
            
        Returns:
            Server instance or None if not found
        """
        return self.servers.get(name)
    
    def list_servers(self) -> List[Server]:
        """
        List all servers.
        
        Returns:
            List of server instances
        """
        return list(self.servers.values())
    
    def update_server(self, name: str, config: ServerConfig) -> Server:
        """
        Update server configuration.
        
        Args:
            name: Server name
            config: New configuration
            
        Returns:
            Updated server instance
            
        Raises:
            ValueError: If server not found
        """
        if name not in self.servers:
            raise ValueError(f"Server '{name}' not found")
        
        # Update timestamp
        config.updated_at = datetime.now()
        
        # Save configuration
        server_dir = self.servers_dir / name
        config_path = server_dir / "server.yml"
        config.save_to_file(str(config_path))
        
        # Update server instance
        server = Server(config, self.plugin_manager, self.workspace_path)
        self.servers[name] = server
        
        logger.info(f"✅ Updated server: {name}")
        return server
    
    def delete_server(self, name: str):
        """
        Delete a server.
        
        Args:
            name: Server name
            
        Raises:
            ValueError: If server not found or is a default server
        """
        if name not in self.servers:
            raise ValueError(f"Server '{name}' not found")
        
        # Prevent deletion of default servers
        if name in ["local", "filmeto"]:
            raise ValueError(f"Cannot delete default server '{name}'")
        
        # Remove from memory
        del self.servers[name]
        
        # Delete directory
        server_dir = self.servers_dir / name
        if server_dir.exists():
            import shutil
            shutil.rmtree(server_dir)
        
        logger.info(f"✅ Deleted server: {name}")
    
    # Routing Operations
    
    def add_routing_rule(self, rule: RoutingRule):
        """Add a routing rule"""
        self.routing_rules.append(rule)
        self.routing_rules.sort(key=lambda r: r.priority, reverse=True)
        self._save_routing_rules()
        logger.info(f"✅ Added routing rule: {rule.name}")
    
    def remove_routing_rule(self, name: str):
        """Remove a routing rule by name"""
        self.routing_rules = [r for r in self.routing_rules if r.name != name]
        self._save_routing_rules()
        logger.info(f"✅ Removed routing rule: {name}")
    
    def get_routing_rules(self) -> List[RoutingRule]:
        """Get all routing rules"""
        return self.routing_rules.copy()
    
    def route_task(self, task: FilmetoTask) -> Optional[Server]:
        """
        Route a task to appropriate server based on routing rules.
        
        Args:
            task: Task to route
            
        Returns:
            Server instance or None if no matching server
        """
        # Try each rule in priority order
        for rule in self.routing_rules:
            if rule.matches(task):
                server = self.get_server(rule.server_name)
                if server and server.is_enabled:
                    return server
        
        # No matching rule, try default server
        default_server = self.get_server("local")
        if default_server and default_server.is_enabled:
            return default_server
        
        return None
    
    def route_task_with_fallback(self, task: FilmetoTask) -> List[Server]:
        """
        Route a task and return list of servers including fallbacks.
        
        Args:
            task: Task to route
            
        Returns:
            List of servers (primary + fallbacks)
        """
        servers = []
        
        # Find matching rule
        for rule in self.routing_rules:
            if rule.matches(task):
                # Add primary server
                primary = self.get_server(rule.server_name)
                if primary and primary.is_enabled:
                    servers.append(primary)
                
                # Add fallback servers
                for fallback_name in rule.fallback_servers:
                    fallback = self.get_server(fallback_name)
                    if fallback and fallback.is_enabled:
                        servers.append(fallback)
                
                break
        
        # If no match, use default
        if not servers:
            default = self.get_server("local")
            if default and default.is_enabled:
                servers.append(default)
        
        return servers
    
    async def execute_task_with_routing(
        self,
        task: FilmetoTask,
        use_fallback: bool = True
    ):
        """
        Execute task with automatic routing, per-server retry, and fallback.

        Each server is retried according to its own ``RetryPolicy`` (derived
        from the plugin's ``execution`` config) before falling through to the
        next fallback server.

        Args:
            task: Task to execute
            use_fallback: Whether to try fallback servers on failure
            
        Yields:
            TaskProgress: Progress updates
            TaskResult: Final result
        """
        if use_fallback:
            servers = self.route_task_with_fallback(task)
        else:
            primary = self.route_task(task)
            servers = [primary] if primary else []
        
        if not servers:
            yield TaskResult(
                task_id=task.task_id,
                status="error",
                error_message="No available server found for task"
            )
            return
        
        last_error: Optional[Exception] = None
        
        for server in servers:
            policy = server.get_retry_policy()
            max_attempts = 1 + policy.max_retries

            for attempt in range(max_attempts):
                try:
                    if attempt > 0:
                        delay = policy.compute_delay(attempt - 1)
                        logger.info(
                            f"Retrying task {task.task_id} on {server.name} "
                            f"(attempt {attempt + 1}/{max_attempts}) "
                            f"after {delay:.1f}s"
                        )
                        yield TaskProgress(
                            task_id=task.task_id,
                            type="progress",
                            percent=0,
                            message=(
                                f"Retrying on {server.name} "
                                f"(attempt {attempt + 1}/{max_attempts})..."
                            ),
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.info(
                            f"Routing task {task.task_id} to server: "
                            f"{server.name}"
                        )

                    async for message in server.execute_task(task):
                        yield message

                        if isinstance(message, dict) and "result" in message:
                            return

                    # Generator exhausted without error — success.
                    return

                except Exception as e:
                    last_error = e
                    is_last_attempt = attempt >= max_attempts - 1
                    if is_last_attempt or not policy.is_retryable(e):
                        logger.warning(
                            f"Server {server.name} failed "
                            f"(attempt {attempt + 1}/{max_attempts}): {e}"
                        )
                        break
                    logger.warning(
                        f"Server {server.name} failed "
                        f"(attempt {attempt + 1}/{max_attempts}, "
                        f"will retry): {e}"
                    )
        
        # All servers (and their retries) exhausted.
        yield TaskResult(
            task_id=task.task_id,
            status="error",
            error_message=f"All servers failed. Last error: {str(last_error)}"
        )
    
    # --- Hot-reload support ------------------------------------------------

    def reload_server(self, name: str):
        """
        Reload a single server's configuration from disk.

        If the server already exists in memory it is replaced; otherwise a new
        server is added.  Called automatically by the config watcher when a
        ``server.yml`` file is modified or created.
        """
        config_path = self.servers_dir / name / "server.yml"
        if not config_path.exists():
            logger.warning(f"Cannot reload server '{name}': config file missing")
            return

        try:
            config = ServerConfig.load_from_file(str(config_path))
            server = Server(config, self.plugin_manager, self.workspace_path)
            self.servers[config.name] = server
            logger.info(f"Reloaded server config: {name}")
        except Exception as e:
            logger.error(f"Failed to reload server '{name}': {e}")

    def reload_routing_rules(self):
        """Reload routing rules from disk."""
        self._load_routing_rules()
        logger.info("Routing rules reloaded from disk")

    def _handle_server_config_deleted(self, name: str):
        """Handle deletion of a server.yml file (called by config watcher)."""
        if name in ("local", "filmeto"):
            logger.warning(
                f"Default server config '{name}' was deleted; "
                "it will be recreated on next restart"
            )
            return
        if name in self.servers:
            del self.servers[name]
            logger.info(f"Server '{name}' removed (config deleted)")

    def start_config_watcher(self):
        """
        Start watching the servers directory for config changes.

        Safe to call multiple times; only the first call starts the observer.
        """
        if self._config_observer is not None:
            return

        if not self.servers_dir.exists():
            logger.warning("Servers dir does not exist; config watcher not started")
            return

        self._config_watcher = _ConfigWatcher(self)
        self._config_observer = Observer()
        self._config_observer.schedule(
            self._config_watcher,
            str(self.servers_dir),
            recursive=True,
        )
        self._config_observer.daemon = True
        self._config_observer.start()
        logger.info(f"Config watcher started on {self.servers_dir}")

    def stop_config_watcher(self):
        """Stop the config file watcher if running."""
        if self._config_watcher is not None:
            self._config_watcher.cancel()
            self._config_watcher = None

        if self._config_observer is not None:
            self._config_observer.stop()
            self._config_observer.join(timeout=5)
            self._config_observer = None
            logger.info("Config watcher stopped")

    # --- Query helpers ----------------------------------------------------

    def list_available_server_types(self) -> List[str]:
        """
        List available server types based on available plugins.
        
        Returns:
            List of server type names
        """
        plugins = self.plugin_manager.list_plugins()
        return list(set(plugin.engine for plugin in plugins if plugin.engine))
    
    def list_available_plugins(self) -> List['ServerInfo']:
        """
        List all available plugins that can be used to create servers.

        Returns:
            List of ServerInfo objects
        """
        return self.plugin_manager.list_plugins()

    def get_plugin_ui_widget(self, plugin_name: str, server_config_dict: Optional[Dict[str, Any]] = None):
        """
        Get custom UI widget from a plugin for configuration purposes.

        Args:
            plugin_name: Name of the plugin
            server_config_dict: Optional server configuration dict for editing existing server

        Returns:
            Custom UI widget or None if not available
        """
        return self.plugin_ui_loader.get_plugin_ui_widget(
            plugin_name,
            workspace_path=self.workspace_path,
            server_config_dict=server_config_dict
        )

    async def cleanup(self):
        """Cleanup resources"""
        self.stop_config_watcher()
        await self.plugin_manager.stop_all_plugins()


if __name__ == "__main__":
    # Example usage
    import sys
    
    async def test_server_manager():
        # Get workspace path
        workspace_path = os.path.join(os.path.dirname(__file__), "..", "workspace", "demo")
        
        # Create server manager
        manager = ServerManager(workspace_path)
        
        # List servers
        print("\n📋 Available servers:")
        for server in manager.list_servers():
            print(f"  - {server.name} ({server.server_type}): enabled={server.is_enabled}")
        
        # List routing rules
        print("\n📋 Routing rules:")
        for rule in manager.get_routing_rules():
            print(f"  - {rule.name}: {rule.server_name} (priority={rule.priority})")
        
        # List available server types
        print("\n📋 Available server types (from plugins):")
        for server_type in manager.list_available_server_types():
            print(f"  - {server_type}")
        
        # Cleanup
        await manager.cleanup()
    
    # Run test
    asyncio.run(test_server_manager())
