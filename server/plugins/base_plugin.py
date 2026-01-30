"""
Base Server Plugin

Base class for all server-side plugins.
Handles JSON-RPC communication via stdin/stdout.
"""

import sys
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Callable, Optional, List
from datetime import datetime


class ToolConfig:
    """
    Configuration for a specific tool supported by a plugin.
    """
    def __init__(self, name: str, description: str, parameters: List[Dict[str, Any]]):
        self.name = name
        self.description = description
        self.parameters = parameters  # List of parameter definitions


class BaseServerPlugin(ABC):
    """
    Base class for server plugins.

    Plugins communicate with the service layer via JSON-RPC over stdin/stdout.
    """

    def __init__(self):
        """Initialize the plugin"""
        self.current_task_id: Optional[str] = None

    @abstractmethod
    async def execute_task(
        self,
        task_data: Dict[str, Any],
        progress_callback: Callable[[float, str, Dict[str, Any]], None]
    ) -> Dict[str, Any]:
        """
        Execute a task and return the result.

        Args:
            task_data: Task data including tool_name, parameters, resources
            progress_callback: Callback to report progress
                               progress_callback(percent, message, data)

        Returns:
            Result dictionary with status, output_files, execution_time, etc.
        """
        pass

    @abstractmethod
    def get_plugin_info(self) -> Dict[str, Any]:
        """
        Get plugin metadata.

        Returns:
            Dictionary with name, version, description, supported_tools
        """
        pass

    @abstractmethod
    def get_supported_tools(self) -> List[ToolConfig]:
        """
        Get list of tools supported by this plugin with their configs.

        Returns:
            List of ToolConfig objects
        """
        pass
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get configuration schema for this plugin.
        
        This schema defines what configuration fields are needed when creating
        a new server instance using this plugin.
        
        Returns:
            Dictionary with configuration schema:
            {
                "fields": [
                    {
                        "name": "field_name",
                        "label": "Display Label",
                        "type": "string|integer|boolean|password|url",
                        "required": True|False,
                        "default": "default_value",
                        "description": "Field description",
                        "placeholder": "Placeholder text"
                    },
                    ...
                ]
            }
        """
        # Default schema with basic fields
        return {
            "fields": [
                {
                    "name": "endpoint",
                    "label": "Endpoint URL",
                    "type": "url",
                    "required": False,
                    "default": "",
                    "description": "Service endpoint URL (if applicable)",
                    "placeholder": "http://localhost:8188"
                },
                {
                    "name": "api_key",
                    "label": "API Key",
                    "type": "password",
                    "required": False,
                    "default": "",
                    "description": "API key for authentication (if required)",
                    "placeholder": "Enter API key"
                }
            ]
        }
    
    def init_ui(self, workspace_path: str, server_config: Optional[Dict[str, Any]] = None):
        """
        Initialize custom UI widget for server configuration.
        
        Plugins can override this method to provide a custom configuration UI
        instead of using the default form-based configuration.
        
        Args:
            workspace_path: Path to workspace directory
            server_config: Optional existing server configuration
            
        Returns:
            QWidget: Custom configuration widget, or None to use default form
        """
        return None
    
    def report_progress(
        self, 
        task_id: str, 
        percent: float, 
        message: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Report progress via stdout.
        
        Args:
            task_id: Task identifier
            percent: Progress percentage (0-100)
            message: Progress message
            data: Optional additional data
        """
        progress_message = {
            "jsonrpc": "2.0",
            "method": "progress",
            "params": {
                "task_id": task_id,
                "type": "progress",
                "percent": percent,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "data": data or {}
            }
        }
        self._write_message(progress_message)
    
    def report_heartbeat(self, task_id: str):
        """
        Report heartbeat to keep connection alive.
        
        Args:
            task_id: Task identifier
        """
        heartbeat_message = {
            "jsonrpc": "2.0",
            "method": "heartbeat",
            "params": {
                "task_id": task_id,
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat()
            }
        }
        self._write_message(heartbeat_message)
    
    def _write_message(self, message: Dict[str, Any]):
        """
        Write JSON message to stdout.
        
        Args:
            message: Message dictionary
        """
        try:
            json_str = json.dumps(message)
            sys.stdout.write(json_str + '\n')
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"Error writing message: {e}\n")
            sys.stderr.flush()
    
    def _read_message(self) -> Optional[Dict[str, Any]]:
        """
        Read JSON message from stdin.
        
        Returns:
            Message dictionary or None if EOF
        """
        try:
            line = sys.stdin.readline()
            if not line:
                return None
            return json.loads(line.strip())
        except json.JSONDecodeError as e:
            sys.stderr.write(f"Error parsing JSON: {e}\n")
            sys.stderr.flush()
            return None
        except Exception as e:
            sys.stderr.write(f"Error reading message: {e}\n")
            sys.stderr.flush()
            return None
    
    async def _handle_execute_task(self, request_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle execute_task JSON-RPC request.
        
        Args:
            request_id: JSON-RPC request ID
            params: Task parameters
        
        Returns:
            JSON-RPC response
        """
        task_id = params.get("task_id")
        self.current_task_id = task_id
        
        try:
            # Report started
            self.report_progress(task_id, 0, "Task started")
            
            # Create progress callback
            def progress_callback(percent: float, message: str, data: Dict[str, Any] = None):
                self.report_progress(task_id, percent, message, data)
            
            # Execute task
            result = await self.execute_task(params, progress_callback)
            
            # Report completed
            self.report_progress(task_id, 100, "Task completed")
            
            # Return success response
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }
            
        except Exception as e:
            # Return error response
            error_result = {
                "task_id": task_id,
                "status": "error",
                "error_message": str(e),
                "output_files": []
            }
            return {
                "jsonrpc": "2.0",
                "result": error_result,
                "id": request_id
            }
        finally:
            self.current_task_id = None
    
    async def _handle_get_info(self, request_id: int) -> Dict[str, Any]:
        """
        Handle get_info JSON-RPC request.

        Args:
            request_id: JSON-RPC request ID

        Returns:
            JSON-RPC response with plugin info
        """
        info = self.get_plugin_info()
        # Add supported tools to the info
        tools = []
        for tool_config in self.get_supported_tools():
            tools.append({
                "name": tool_config.name,
                "description": tool_config.description,
                "parameters": tool_config.parameters
            })

        info["supported_tools"] = tools
        return {
            "jsonrpc": "2.0",
            "result": info,
            "id": request_id
        }
    
    async def _handle_ping(self, request_id: int) -> Dict[str, Any]:
        """
        Handle ping JSON-RPC request.
        
        Args:
            request_id: JSON-RPC request ID
        
        Returns:
            JSON-RPC response with pong
        """
        return {
            "jsonrpc": "2.0",
            "result": {"status": "pong"},
            "id": request_id
        }
    
    async def _handle_request(self, request: Dict[str, Any]):
        """
        Handle JSON-RPC request.
        
        Args:
            request: JSON-RPC request
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        response = None
        
        if method == "execute_task":
            response = await self._handle_execute_task(request_id, params)
        elif method == "get_info":
            response = await self._handle_get_info(request_id)
        elif method == "ping":
            response = await self._handle_ping(request_id)
        else:
            # Unknown method
            response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": request_id
            }
        
        if response:
            self._write_message(response)
    
    def run(self):
        """
        Main loop: read from stdin, process requests, write to stdout.
        
        This is the entry point for the plugin process.
        """
        async def main_loop():
            # Send initial ready message
            ready_message = {
                "jsonrpc": "2.0",
                "method": "ready",
                "params": self.get_plugin_info()
            }
            self._write_message(ready_message)
            
            # Process requests
            while True:
                request = self._read_message()
                if request is None:
                    # EOF or error, exit
                    break
                
                await self._handle_request(request)
        
        # Run event loop
        try:
            asyncio.run(main_loop())
        except KeyboardInterrupt:
            sys.stderr.write("Plugin interrupted\n")
        except Exception as e:
            logger.error(f"Plugin error: {e}", exc_info=True)

