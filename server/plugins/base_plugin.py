"""
Base Server Plugin

Base class for all server-side plugins.
Handles JSON-RPC communication via stdin/stdout.
"""

import sys
import json
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Callable, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Default heartbeat interval in seconds
DEFAULT_HEARTBEAT_INTERVAL = 30


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

    def __init__(self, heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL):
        """
        Initialize the plugin.

        Args:
            heartbeat_interval: Interval in seconds between heartbeat messages.
                               Set to 0 to disable automatic heartbeats.
        """
        self.current_task_id: Optional[str] = None
        self.heartbeat_interval = heartbeat_interval

        # Async I/O components (initialized in run())
        self._stdin_reader: Optional[asyncio.StreamReader] = None
        self._stdout_writer: Optional[asyncio.StreamWriter] = None
        self._running = False
        self._active_tasks: Dict[str, asyncio.Task] = {}

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
        Write JSON message to stdout (synchronous, for backward compatibility).

        This method is kept for synchronous contexts like progress callbacks.
        For async contexts, prefer _async_write_message.

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

    async def _async_write_message(self, message: Dict[str, Any]):
        """
        Write JSON message to stdout (asynchronous).

        Args:
            message: Message dictionary
        """
        try:
            json_str = json.dumps(message)
            if self._stdout_writer:
                self._stdout_writer.write((json_str + '\n').encode())
                await self._stdout_writer.drain()
            else:
                # Fallback to sync write if writer not initialized
                self._write_message(message)
        except Exception as e:
            sys.stderr.write(f"Error writing message: {e}\n")
            sys.stderr.flush()

    def _read_message(self) -> Optional[Dict[str, Any]]:
        """
        Read JSON message from stdin (synchronous, for backward compatibility).

        Note: This method blocks. For async contexts, use _async_read_message.

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

    async def _async_read_message(self) -> Optional[Dict[str, Any]]:
        """
        Read JSON message from stdin (asynchronous, non-blocking).

        Returns:
            Message dictionary or None if EOF
        """
        try:
            if self._stdin_reader:
                line = await self._stdin_reader.readline()
                if not line:
                    return None
                return json.loads(line.decode().strip())
            else:
                # Fallback to sync read if reader not initialized
                return self._read_message()
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
            await self._async_write_message(response)
    
    def run(self):
        """
        Main loop with async I/O: read from stdin, process requests, write to stdout.

        This is the entry point for the plugin process. Uses asyncio for:
        - Non-blocking stdin/stdout I/O
        - Concurrent request handling
        - Periodic heartbeat messages
        """
        async def setup_async_io():
            """Setup async stdin/stdout streams."""
            loop = asyncio.get_event_loop()

            # Setup stdin reader
            self._stdin_reader = asyncio.StreamReader()
            stdin_protocol = asyncio.StreamReaderProtocol(self._stdin_reader)
            await loop.connect_read_pipe(lambda: stdin_protocol, sys.stdin)

            # Setup stdout writer
            writer_transport, writer_protocol = await loop.connect_write_pipe(
                asyncio.streams.FlowControlMixin,
                sys.stdout
            )
            self._stdout_writer = asyncio.StreamWriter(
                writer_transport, writer_protocol, None, loop
            )

        async def send_ready_message():
            """Send initial ready message."""
            ready_message = {
                "jsonrpc": "2.0",
                "method": "ready",
                "params": self.get_plugin_info()
            }
            await self._async_write_message(ready_message)
            logger.info(f"Plugin {self.__class__.__name__} ready")

        async def read_loop():
            """Read and process requests from stdin."""
            while self._running:
                try:
                    request = await self._async_read_message()
                    if request is None:
                        # EOF, exit gracefully
                        logger.info("stdin EOF received, exiting")
                        break

                    # Handle request concurrently (don't block reading next request)
                    task = asyncio.create_task(self._handle_request(request))

                    # Track task if it has a task_id
                    if isinstance(request.get("params"), dict):
                        task_id = request["params"].get("task_id")
                        if task_id:
                            self._active_tasks[task_id] = task
                            # Clean up task when done
                            def cleanup_task(t, tid=task_id):
                                self._active_tasks.pop(tid, None)
                            task.add_done_callback(cleanup_task)

                except asyncio.CancelledError:
                    logger.debug("Read loop cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in read loop: {e}", exc_info=True)
                    # Continue reading after error
                    continue

        async def heartbeat_loop():
            """Send periodic heartbeat messages when idle."""
            if self.heartbeat_interval <= 0:
                logger.debug("Heartbeat disabled (interval <= 0)")
                return

            logger.debug(f"Heartbeat loop started (interval: {self.heartbeat_interval}s)")

            while self._running:
                try:
                    await asyncio.sleep(self.heartbeat_interval)

                    # Only send heartbeat when not executing a task
                    # (task execution sends its own progress/heartbeats)
                    if self.current_task_id is None:
                        heartbeat_message = {
                            "jsonrpc": "2.0",
                            "method": "heartbeat",
                            "params": {
                                "type": "idle",
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                        await self._async_write_message(heartbeat_message)
                        logger.debug("Idle heartbeat sent")

                except asyncio.CancelledError:
                    logger.debug("Heartbeat loop cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in heartbeat loop: {e}", exc_info=True)
                    continue

        async def main():
            """Main async entry point."""
            try:
                # Setup async I/O
                await setup_async_io()
                self._running = True

                # Send ready message
                await send_ready_message()

                # Run read and heartbeat loops concurrently
                tasks = [asyncio.create_task(read_loop())]

                if self.heartbeat_interval > 0:
                    tasks.append(asyncio.create_task(heartbeat_loop()))

                # Wait for read_loop to finish (on EOF)
                # heartbeat_loop runs until cancelled
                done, pending = await asyncio.wait(
                    tasks,
                    return_when=asyncio.FIRST_COMPLETED
                )

                # Cancel pending tasks (heartbeat_loop)
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            except Exception as e:
                logger.error(f"Plugin error: {e}", exc_info=True)
            finally:
                self._running = False

                # Wait for any active tasks to complete (with timeout)
                if self._active_tasks:
                    logger.info(f"Waiting for {len(self._active_tasks)} active tasks to complete...")
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*self._active_tasks.values(), return_exceptions=True),
                            timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        logger.warning("Timeout waiting for active tasks, forcing exit")

                # Cleanup
                if self._stdout_writer:
                    self._stdout_writer.close()
                    try:
                        await self._stdout_writer.wait_closed()
                    except Exception:
                        pass

                logger.info("Plugin shutdown complete")

        # Run event loop
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info("Plugin interrupted by user")
        except Exception as e:
            logger.error(f"Plugin error: {e}", exc_info=True)
            sys.exit(1)

