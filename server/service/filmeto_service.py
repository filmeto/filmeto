"""
Filmeto Service

Core service layer that manages task execution through plugins.
"""

import asyncio
import logging
import os
import time
from collections import OrderedDict
from typing import AsyncIterator, Dict, Optional, Union
from datetime import datetime
from pathlib import Path

import structlog

from server.api.types import (
    FilmetoTask, TaskProgress, TaskResult, ProgressType,
    ValidationError, ServerNotFoundError, ServerExecutionError, TimeoutError as TaskTimeoutError
)
from server.api.resource_processor import ResourceProcessor
from server.plugins.plugin_manager import PluginManager
from utils.logging_utils import TaskMetrics

logger = structlog.get_logger(__name__)


class TaskStatusStore:
    """In-memory store for task status with LRU eviction and TTL expiry."""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self._store: OrderedDict[str, dict] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl

    def set(self, task_id: str, status: str, **kwargs):
        if task_id in self._store:
            self._store.move_to_end(task_id)
            entry = self._store[task_id]
        else:
            if len(self._store) >= self._max_size:
                self._store.popitem(last=False)
            entry = {"task_id": task_id, "created_at": time.time()}
            self._store[task_id] = entry

        entry["status"] = status
        entry["updated_at"] = time.time()
        entry.update(kwargs)

    def get(self, task_id: str) -> Optional[dict]:
        entry = self._store.get(task_id)
        if entry is None:
            return None
        if time.time() - entry["updated_at"] > self._ttl:
            del self._store[task_id]
            return None
        self._store.move_to_end(task_id)
        return dict(entry)


class TaskQueue:
    """Semaphore-based concurrency limiter with observability."""

    def __init__(self, max_concurrent: int = 5):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        self._active_tasks: Dict[str, float] = {}
        self._queued_count = 0
        self._lock = asyncio.Lock()

    async def acquire(self, task_id: str):
        """Acquire a concurrency slot. Blocks if at capacity."""
        async with self._lock:
            self._queued_count += 1
        try:
            await self._semaphore.acquire()
        finally:
            async with self._lock:
                self._queued_count -= 1
                self._active_tasks[task_id] = time.time()

    def release(self, task_id: str):
        """Release a concurrency slot."""
        self._active_tasks.pop(task_id, None)
        self._semaphore.release()

    @property
    def info(self) -> dict:
        return {
            "max_concurrent": self._max_concurrent,
            "active_count": len(self._active_tasks),
            "queued_count": self._queued_count,
            "active_task_ids": list(self._active_tasks.keys()),
        }

    @property
    def is_at_capacity(self) -> bool:
        return len(self._active_tasks) >= self._max_concurrent


class FilmetoService:
    """
    Service layer managing plugin lifecycle and task execution.
    """
    
    def __init__(self, plugins_dir: str = None, cache_dir: str = None,
                 workspace_path: str = None, max_concurrent_tasks: int = 5):
        """
        Initialize Filmeto service.
        
        Args:
            plugins_dir: Directory containing plugins
            cache_dir: Directory for resource caching
            workspace_path: Path to workspace directory
            max_concurrent_tasks: Maximum number of tasks executing concurrently
        """
        # Determine workspace path
        if workspace_path:
            self.workspace_path = Path(workspace_path)
        else:
            project_root = Path(__file__).parent.parent.parent
            self.workspace_path = project_root / "workspace"
        
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        from server.server import ServerManager
        self.plugin_manager = PluginManager(plugins_dir)
        self.server_manager = ServerManager(str(self.workspace_path), self.plugin_manager)
        self.resource_processor = ResourceProcessor(cache_dir)
        self.heartbeat_interval = 5  # seconds
        self._task_store = TaskStatusStore()
        self._task_queue = TaskQueue(max_concurrent=max_concurrent_tasks)
        self._background_tasks: Dict[str, asyncio.Task] = {}
        
        # Discover plugins on initialization
        self.plugin_manager.discover_plugins()
    
    async def execute_task_stream(
        self, 
        task: FilmetoTask
    ) -> AsyncIterator[Union[TaskProgress, TaskResult]]:
        """
        Execute task through appropriate server with streaming.
        
        Args:
            task: Task to execute
            
        Yields:
            TaskProgress: Progress updates during execution
            TaskResult: Final result (last item)
            
        Raises:
            ValidationError: If task validation fails
            ServerNotFoundError: If server not found
            ServerExecutionError: If server execution fails
            TaskTimeoutError: If task exceeds timeout
        """
        start_time = datetime.now()
        log = logger.bind(task_id=task.task_id, capability=task.capability.value,
                          server=task.server_name)
        metrics = TaskMetrics(task_id=task.task_id,
                              capability=task.capability.value,
                              server=task.server_name)
        
        # Validate task
        is_valid, error_msg = task.validate()
        if not is_valid:
            self._task_store.set(task.task_id, "error", error_message=error_msg)
            log.warning("task_validation_failed", error=error_msg)
            raise ValidationError(error_msg, {"task_id": task.task_id})
        
        log.info("task_accepted")

        # Wait for a concurrency slot
        if self._task_queue.is_at_capacity:
            self._task_store.set(task.task_id, "queued", message="Waiting for available slot...")
            log.info("task_queued")
            yield TaskProgress(
                task_id=task.task_id,
                type=ProgressType.STARTED,
                percent=0,
                message="Queued, waiting for available slot..."
            )

        await self._task_queue.acquire(task.task_id)
        metrics.mark("queue_wait")
        
        self._task_store.set(task.task_id, "running", percent=0, message="Starting...")
        log.info("task_started")
        
        try:
            # Process resources
            yield TaskProgress(
                task_id=task.task_id,
                type=ProgressType.STARTED,
                percent=0,
                message="Processing resources..."
            )
            
            processed_resources = []
            for i, resource in enumerate(task.resources):
                try:
                    local_path = await self.resource_processor.process_resource(resource)
                    processed_resources.append(local_path)
                    
                    percent = (i + 1) / len(task.resources) * 10
                    yield TaskProgress(
                        task_id=task.task_id,
                        type=ProgressType.PROGRESS,
                        percent=percent,
                        message=f"Processed resource {i+1}/{len(task.resources)}"
                    )
                except Exception as e:
                    raise ValidationError(
                        f"Failed to process resource {i}: {str(e)}",
                        {"task_id": task.task_id, "resource_index": i}
                    )

            metrics.mark("resource_processing")
            
            # Update task with processed resource paths
            task.metadata['processed_resources'] = processed_resources
            
            # Execute task with routing via ServerManager
            yield TaskProgress(
                task_id=task.task_id,
                type=ProgressType.PROGRESS,
                percent=10,
                message="Routing task to server..."
            )
            
            async for update in self.server_manager.execute_task_with_routing(task):
                if isinstance(update, TaskProgress):
                    scaled_percent = 10 + (update.percent * 0.85)
                    update.percent = scaled_percent
                    self._task_store.set(
                        task.task_id, "running",
                        percent=scaled_percent, message=update.message,
                    )
                    yield update
                elif isinstance(update, TaskResult):
                    self._task_store.set(
                        task.task_id, update.status,
                        percent=100,
                        output_files=update.output_files,
                        error_message=update.error_message,
                        execution_time=update.execution_time,
                    )
                    metrics.mark("plugin_execution")
                    metrics.finish(status=update.status)
                    log.info("task_completed", **metrics.to_dict())
                    yield update
                elif isinstance(update, dict):
                    method = update.get("method")
                    result = update.get("result")
                    
                    if method == "progress":
                        params = update.get("params", {})
                        percent = params.get("percent", 0)
                        scaled_percent = 10 + (percent * 0.85)
                        
                        yield TaskProgress(
                            task_id=task.task_id,
                            type=ProgressType(params.get("type", "progress")),
                            percent=scaled_percent,
                            message=params.get("message", ""),
                            data=params.get("data", {})
                        )
                    elif method == "heartbeat":
                        yield TaskProgress(
                            task_id=task.task_id,
                            type=ProgressType.HEARTBEAT,
                            percent=0,
                            message="heartbeat"
                        )
                    elif result:
                        execution_time = (datetime.now() - start_time).total_seconds()
                        
                        task_result = TaskResult(
                            task_id=task.task_id,
                            status=result.get("status", "error"),
                            output_files=result.get("output_files", []),
                            output_resources=result.get("output_resources", []),
                            error_message=result.get("error_message", ""),
                            execution_time=execution_time,
                            metadata=result.get("metadata", {})
                        )
                        self._task_store.set(
                            task.task_id, task_result.status,
                            percent=100,
                            output_files=task_result.output_files,
                            error_message=task_result.error_message,
                            execution_time=execution_time,
                        )
                        metrics.mark("plugin_execution")
                        metrics.finish(status=task_result.status)
                        log.info("task_completed", **metrics.to_dict())
                        yield task_result
        
        except asyncio.TimeoutError:
            self._task_store.set(
                task.task_id, "timeout",
                error_message=f"Task exceeded {task.timeout}s timeout",
            )
            metrics.finish(status="timeout")
            log.error("task_timeout", **metrics.to_dict())
            raise TaskTimeoutError(task.task_id, task.timeout)
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            error_result = TaskResult(
                task_id=task.task_id,
                status="error",
                error_message=str(e),
                execution_time=execution_time
            )
            self._task_store.set(
                task.task_id, "error",
                error_message=str(e),
                execution_time=execution_time,
            )
            metrics.finish(status="error")
            log.error("task_failed", error=str(e), **metrics.to_dict(),
                       exc_info=True)
            
            yield error_result
        
        finally:
            self._task_queue.release(task.task_id)
    
    async def _send_heartbeats(self, task_id: str, plugin):
        """
        Send periodic heartbeats while task is executing.
        
        Args:
            task_id: Task identifier
            plugin: Plugin process
        """
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                # Heartbeats are sent by the plugin itself
                # This is just to keep the connection alive on the service side
        except asyncio.CancelledError:
            pass
    
    async def enqueue_task(self, task: FilmetoTask, priority: int = 0) -> str:
        """
        Enqueue a task for background execution (non-streaming).

        The task is validated immediately, then executed asynchronously.
        Use get_task_status() to poll for progress and results.

        Args:
            task: Task to execute
            priority: Lower values run first (unused for now, reserved for future priority queue)

        Returns:
            task_id for status polling
        """
        is_valid, error_msg = task.validate()
        if not is_valid:
            self._task_store.set(task.task_id, "error", error_message=error_msg)
            raise ValidationError(error_msg, {"task_id": task.task_id})

        self._task_store.set(task.task_id, "queued", message="Enqueued for background execution")

        async def _run_background():
            try:
                async for _ in self.execute_task_stream(task):
                    pass
            except Exception as e:
                logger.error(f"Background task {task.task_id} failed: {e}")
            finally:
                self._background_tasks.pop(task.task_id, None)

        bg_task = asyncio.create_task(_run_background())
        self._background_tasks[task.task_id] = bg_task
        return task.task_id

    def get_queue_info(self) -> dict:
        """Return current queue and concurrency status."""
        info = self._task_queue.info
        info["background_task_count"] = len(self._background_tasks)
        return info

    async def get_task_status(self, task_id: str) -> dict:
        """
        Get current status of a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task status dictionary
        """
        entry = self._task_store.get(task_id)
        if entry is None:
            return {"task_id": task_id, "status": "not_found"}
        return entry
    
    def list_plugins(self) -> list:
        """
        List all available plugins with their supported tools.

        Returns:
            List of plugin info dictionaries
        """
        plugins = self.plugin_manager.list_plugins()
        result = []
        for p in plugins:
            abilities = [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "parameters": cap.parameters,
                }
                for cap in p.capabilities
            ]
            entry = {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "engine": p.engine,
                "author": p.author,
                "abilities": abilities,
                "tools": abilities,
            }
            if len(abilities) == 1:
                entry["ability"] = abilities[0]["name"]
            result.append(entry)
        return result

    def get_plugins_by_tool(self, tool_name) -> list:
        """
        Return plugin info dicts that declare the given ability name (e.g. ``text2image``).

        Accepts a string or an Enum-like value with ``.value``.
        """
        key = tool_name.value if hasattr(tool_name, "value") else str(tool_name)
        return [
            p
            for p in self.list_plugins()
            if any(a.get("name") == key for a in p.get("abilities", []))
        ]

    def list_tools(self) -> list:
        """
        List all available tools across plugins.

        Returns:
            List of capability info dictionaries
        """
        # Get unique capabilities from all servers
        all_capabilities = set()
        plugins = self.plugin_manager.list_plugins()

        for plugin in plugins:
            for capability in plugin.capabilities:
                all_capabilities.add(capability.name)

        return [
            {
                "name": cap_name,
                "display_name": cap_name.replace('2', ' to ').title()
            }
            for cap_name in sorted(list(all_capabilities))
        ]

    def get_capability_details(self, capability_name: str) -> dict:
        """
        Get detailed information about a specific capability.

        Args:
            capability_name: Name of the capability to query

        Returns:
            Capability details including parameters and supporting servers
        """
        plugins = self.plugin_manager.list_plugins()
        supporting_servers = []

        for plugin in plugins:
            for capability in plugin.capabilities:
                if capability.name == capability_name:
                    supporting_servers.append({
                        "server_name": plugin.name,
                        "server_version": plugin.version,
                        "server_description": plugin.description,
                        "parameters": capability.parameters
                    })

        return {
            "name": capability_name,
            "display_name": capability_name.replace('2', ' to ').title(),
            "supporting_servers": supporting_servers
        }
    
    async def cleanup(self):
        """
        Cleanup resources, cancel background tasks, and stop all plugins.
        """
        for task_id, bg_task in list(self._background_tasks.items()):
            bg_task.cancel()
            logger.info(f"Cancelled background task: {task_id}")
        self._background_tasks.clear()

        await self.plugin_manager.stop_all_plugins()
        self.resource_processor.cleanup_cache()


