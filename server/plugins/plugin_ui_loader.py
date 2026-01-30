"""
Plugin UI Loader

Handles loading plugin UI components for configuration purposes.
This module loads plugins via code import (not subprocess) to enable
UI widget instantiation in the main process.
"""

import sys
import importlib.util
from pathlib import Path
from typing import Optional, Dict, Any, Type

from PySide6.QtWidgets import QWidget

from server.plugins.plugin_manager import PluginInfo


class PluginUILoader:
    """
    Loads plugin UI components via code import.
    
    This class is responsible for loading plugin classes in the main process
    to enable UI widget creation. It should NOT be used for task execution,
    which should go through PluginManager's subprocess-based execution.
    """
    
    def __init__(self, plugins_dir: Optional[Path] = None):
        """
        Initialize plugin UI loader.
        
        Args:
            plugins_dir: Directory containing plugins (default: server/plugins/)
        """
        if plugins_dir:
            self.plugins_dir = Path(plugins_dir)
        else:
            # Default to server/plugins directory
            self.plugins_dir = Path(__file__).parent
    
    def get_plugin_directory(self, plugin_name: str) -> Optional[Path]:
        """
        Find the plugin directory based on plugin name.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Path to plugin directory or None if not found
        """
        # Try to match by plugin name as stored in plugin config
        # We need to scan plugin.yml files to find matching names
        if not self.plugins_dir.exists():
            return None
        
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith('_'):
                continue
            
            # Check if this directory has a plugin.yml with matching name
            config_file = plugin_dir / "plugin.yml"
            if config_file.exists():
                import yaml
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    if config.get('name', '').lower() == plugin_name.lower():
                        return plugin_dir
                except Exception:
                    continue
        
        return None
    
    def load_plugin_class(self, plugin_dir: Path) -> Optional[Type]:
        """
        Load the plugin class from its main module.
        
        Args:
            plugin_dir: Path to the plugin directory
            
        Returns:
            Plugin class or None if failed
        """
        main_file = plugin_dir / "main.py"
        if not main_file.exists():
            return None
        
        # Create a unique module name to avoid conflicts
        plugin_name = plugin_dir.name
        module_name = f"plugin_{plugin_name.replace('-', '_')}_ui_loader"
        
        # Check if module already exists in sys.modules
        if module_name in sys.modules:
            module = sys.modules[module_name]
        else:
            # Import the plugin module
            spec = importlib.util.spec_from_file_location(module_name, main_file)
            if not spec or not spec.loader:
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            
            # Execute the module
            try:
                spec.loader.exec_module(module)
            except Exception as e:
                logger.error(f"Failed to load plugin module {module_name}: {e}", exc_info=True)
                return None
        
        # Find the plugin class
        # Look for classes that have init_ui and get_plugin_info methods
        # and are subclasses of BaseServerPlugin
        plugin_class = None
        
        # Try to get BaseServerPlugin from the module for subclass checking
        BaseServerPlugin = None
        for name in dir(module):
            obj = getattr(module, name)
            if name == 'BaseServerPlugin' and isinstance(obj, type):
                BaseServerPlugin = obj
                break
        
        # If BaseServerPlugin not found in module, try to import it
        if BaseServerPlugin is None:
            try:
                from server.plugins.base_plugin import BaseServerPlugin
            except ImportError:
                pass
        
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and
                hasattr(obj, 'init_ui') and
                hasattr(obj, 'get_plugin_info') and
                name != 'BaseServerPlugin'):
                # Check if it's a subclass of BaseServerPlugin if available
                if BaseServerPlugin and issubclass(obj, BaseServerPlugin):
                    plugin_class = obj
                    break
                elif BaseServerPlugin is None:
                    # If we can't check subclass, just use the first matching class
                    plugin_class = obj
                    break
        
        return plugin_class
    
    def create_plugin_ui_instance(self, plugin_dir: Path) -> Optional[Any]:
        """
        Create a plugin instance for UI purposes.
        
        Args:
            plugin_dir: Path to the plugin directory
            
        Returns:
            Plugin instance or None if failed
        """
        plugin_class = self.load_plugin_class(plugin_dir)
        if not plugin_class:
            return None
        
        # Create plugin instance - this will be for UI only, not for actual task execution
        try:
            plugin_instance = plugin_class()
            return plugin_instance
        except Exception as e:
            logger.error(f"Failed to instantiate plugin class {plugin_class.__name__}: {e}", exc_info=True)
            return None
    
    def get_plugin_ui_widget(
        self,
        plugin_name: str,
        workspace_path: Optional[Path] = None,
        server_config_dict: Optional[Dict[str, Any]] = None
    ) -> Optional[QWidget]:
        """
        Get custom UI widget from a plugin for configuration purposes.
        
        Args:
            plugin_name: Name of the plugin
            workspace_path: Path to workspace directory
            server_config_dict: Optional server configuration dict for editing existing server
            
        Returns:
            Custom UI widget or None if not available
        """
        try:
            # Get the plugin directory based on plugin name
            plugin_dir = self.get_plugin_directory(plugin_name)
            
            if not plugin_dir:
                print(f"Plugin directory not found for: {plugin_name}")
                return None
            
            # Import and instantiate the plugin class to get custom UI
            plugin_instance = self.create_plugin_ui_instance(plugin_dir)
            
            if not plugin_instance:
                print(f"Failed to create plugin instance for: {plugin_name}")
                return None
            
            # Call init_ui method with workspace path and server config
            if workspace_path is None:
                # Try to get workspace path from a default location
                workspace_path = Path.cwd() / "workspace"
            
            custom_widget = plugin_instance.init_ui(str(workspace_path), server_config_dict)
            
            return custom_widget
            
        except Exception as e:
            logger.error(f"Failed to get custom UI from plugin {plugin_name}: {e}", exc_info=True)
            return None
    
    def get_plugin_info_from_code(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get plugin info by loading the plugin class directly (not from plugin.yml).
        
        This can be useful for getting runtime plugin information.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin info dictionary or None if failed
        """
        try:
            plugin_dir = self.get_plugin_directory(plugin_name)
            if not plugin_dir:
                return None
            
            plugin_instance = self.create_plugin_ui_instance(plugin_dir)
            if not plugin_instance:
                return None
            
            return plugin_instance.get_plugin_info()
            
        except Exception as e:
            print(f"Failed to get plugin info from code for {plugin_name}: {e}")
            return None

