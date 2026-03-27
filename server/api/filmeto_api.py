"""
Filmeto API

Unified API interface for AI model services.
Supports both web-based access and local in-app calls with streaming.
"""

from __future__ import annotations
from typing import AsyncIterator, List, Union, Optional, Dict, Any

from server.api.types import FilmetoTask, TaskProgress, TaskResult, ValidationError, Capability
from server.api.chat_types import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChunk,
    ModelInfo,
)


class FilmetoApi:
    """
    Unified API interface for Filmeto AI services.

    This class provides a clean interface for both web and local clients
    to execute tasks and receive streaming progress updates.
    """

    def __init__(self, plugins_dir: Optional[str] = None, cache_dir: Optional[str] = None, workspace_path: Optional[str] = None):
        """
        Initialize Filmeto API.

        Args:
            plugins_dir: Directory containing server plugins
            cache_dir: Directory for resource caching
            workspace_path: Path to workspace directory
        """
        from server.service.filmeto_service import FilmetoService
        from server.service.chat_service import ChatService
        from server.service.capability_service import CapabilityService
        from server.service.ability_selection_service import AbilitySelectionService

        self.service = FilmetoService(plugins_dir, cache_dir, workspace_path)
        self.chat_service = ChatService(self.service.server_manager)
        self.capability_service = CapabilityService(self.service.server_manager)
        self.selection_service = AbilitySelectionService(self.service.server_manager)

    async def execute_task_stream(
        self,
        task: FilmetoTask
    ) -> AsyncIterator[Union[TaskProgress, TaskResult]]:
        """
        Execute a task and stream progress updates.

        This is the main entry point for task execution. It validates the task,
        processes resources, routes to the appropriate server, and streams
        progress updates and the final result.

        Args:
            task: Task to execute

        Yields:
            TaskProgress: Progress updates during execution
            TaskResult: Final result (last item yielded)

        Raises:
            ValidationError: If task validation fails
            ServerNotFoundError: If specified server not found
            ServerExecutionError: If server execution fails
            TimeoutError: If task exceeds timeout

        Example:
            ```python
            api = FilmetoApi()
            task = FilmetoTask(
                capability=Capability.TEXT2IMAGE,
                server_name="bailian",
                parameters={"prompt": "a beautiful sunset"}
            )

            async for update in api.execute_task_stream(task):
                if isinstance(update, TaskProgress):
                    print(f"Progress: {update.percent}% - {update.message}")
                elif isinstance(update, TaskResult):
                    print(f"Result: {update.status}, files: {update.output_files}")
            ```
        """
        async for update in self.service.execute_task_stream(task):
            yield update

    def validate_task(self, task: FilmetoTask) -> tuple[bool, Optional[str]]:
        """
        Validate task structure and parameters.

        Args:
            task: Task to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        return task.validate()

    async def enqueue_task(self, task: FilmetoTask, priority: int = 0) -> str:
        """
        Enqueue a task for background execution.

        Args:
            task: Task to execute
            priority: Lower values run first

        Returns:
            task_id for status polling
        """
        return await self.service.enqueue_task(task, priority)

    def get_queue_info(self) -> dict:
        """Return current queue and concurrency status."""
        return self.service.get_queue_info()

    async def get_task_status(self, task_id: str) -> dict:
        """
        Get current status of a task.

        Args:
            task_id: Task identifier

        Returns:
            Task status dictionary
        """
        return await self.service.get_task_status(task_id)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List discovered server plugins and their declared abilities."""
        return self.service.list_plugins()

    def get_plugins_by_tool(self, tool_name) -> List[Dict[str, Any]]:
        """Plugins that expose a given ability name (e.g. ``text2image``)."""
        return self.service.get_plugins_by_tool(tool_name)

    def list_capabilities(self, capability_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all capability instances, optionally filtered by type.

        Args:
            capability_type: Optional capability type filter (e.g., "text2image")

        Returns:
            List of capability instance dictionaries

        Example:
            ```python
            api = FilmetoApi()
            # Get all capabilities
            all_caps = api.list_capabilities()
            # Get only text2image capabilities
            t2i_caps = api.list_capabilities("text2image")
            ```
        """
        if capability_type:
            try:
                cap = Capability(capability_type)
                instances = self.capability_service.get_capabilities_by_type(cap)
            except ValueError:
                return []
        else:
            instances = self.capability_service.get_all_capabilities()

        return [inst.to_dict() for inst in instances]

    def get_capability(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific capability instance by key.

        Args:
            key: Capability key in "server:model" format

        Returns:
            Capability instance dictionary or None if not found

        Example:
            ```python
            api = FilmetoApi()
            cap = api.get_capability("bailian-prod:wanx2.1-t2i-turbo")
            if cap:
                print(f"Description: {cap['description']}")
            ```
        """
        instance = self.capability_service.get_capability(key)
        return instance.to_dict() if instance else None

    def get_capability_groups(self) -> List[Dict[str, Any]]:
        """
        Get all capabilities grouped by capability type.

        Returns:
            List of capability group dictionaries

        Example:
            ```python
            api = FilmetoApi()
            groups = api.get_capability_groups()
            for group in groups:
                print(f"{group['capability_name']}: {group['total_instances']} options")
            ```
        """
        groups = self.capability_service.get_capability_groups()
        return [g.to_dict() for g in groups]

    def get_capability_selection_context(
        self,
        capability_type: str,
        user_requirement: str = ""
    ) -> Dict[str, Any]:
        """
        Get context for LLM to select appropriate capability.

        This method returns structured information that can be used
        by an LLM to select the most appropriate capability instance
        based on user requirements.

        Args:
            capability_type: Capability type needed (e.g., "text2image")
            user_requirement: User's requirement description

        Returns:
            Dict with capability info for LLM selection
        """
        try:
            cap = Capability(capability_type)
            return self.capability_service.get_llm_selection_context(cap, user_requirement)
        except ValueError:
            return {
                "capability_type": capability_type,
                "available": False,
                "message": f"Unknown capability type: {capability_type}"
            }

    def refresh_capabilities(self) -> None:
        """
        Refresh the capability cache.

        Call this method when server configurations change.
        Also refreshes the selection service cache to stay consistent.
        """
        self.capability_service.refresh_capabilities()
        # Also refresh selection service to keep caches consistent
        if hasattr(self, 'selection_service') and self.selection_service is not None:
            self.selection_service.refresh_capabilities()

    # ------------------------------------------------------------------
    # Chat Completion API (OpenAI-compatible)
    # ------------------------------------------------------------------

    async def chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """
        Execute a non-streaming chat completion.

        Args:
            request: OpenAI-compatible chat completion request

        Returns:
            ChatCompletionResponse
        """
        return await self.chat_service.chat_completion(request)

    async def chat_completion_stream(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[ChatCompletionChunk]:
        """
        Execute a streaming chat completion.

        Args:
            request: OpenAI-compatible chat completion request

        Yields:
            ChatCompletionChunk for each token/fragment
        """
        async for chunk in self.chat_service.chat_completion_stream(request):
            yield chunk

    def list_chat_models(self) -> List[ModelInfo]:
        """
        List all models advertised by chat-capable servers.

        Returns:
            List of ModelInfo
        """
        return self.chat_service.list_models()

    async def cleanup(self):
        """
        Cleanup resources and stop all servers.

        Should be called when shutting down the API.
        """
        await self.service.cleanup()