"""
Chat Completion Service

Routes OpenAI-compatible chat completion requests to configured LLM backends.
Each backend is represented as a Server with server_type set to one of
"openai", "chat", or "llm". The actual LLM call is delegated to the server's
plugin via ServerManager.execute_task().

Server configuration example (server.yml):
    name: my-openai
    server_type: openai
    plugin_name: ""
    endpoint: https://api.openai.com/v1
    api_key: sk-xxx
    parameters:
      provider: openai
      default_model: gpt-4
      models:
        - gpt-4
        - gpt-4-turbo
        - gpt-3.5-turbo
      temperature: 0.7
      max_tokens: 4096
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import TYPE_CHECKING, AsyncIterator, List, Optional

from server.plugins.ability_model_config import is_model_enabled_for_ability
from server.service.ability_selection_service import AbilitySelectionService, SelectionError

from server.api.chat_types import (
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    DeltaMessage,
    ModelInfo,
    UsageInfo,
)
from server.api.types import Capability, FilmetoTask, SelectionConfig, SelectionMode, TaskProgress, TaskResult

if TYPE_CHECKING:
    from server.server import ServerConfig, ServerManager

logger = logging.getLogger(__name__)

CHAT_SERVER_TYPES = frozenset({"chat", "openai", "llm", "bailian"})


def _advertised_chat_model_ids(cfg: "ServerConfig") -> List[str]:
    """Model ids from parameters that are enabled for ``chat_completion``."""
    ids: List[str] = list(cfg.parameters.get("models", []) or [])
    default_model = cfg.parameters.get("default_model")
    if default_model and default_model not in ids:
        ids.append(default_model)
    return [
        mid
        for mid in ids
        if is_model_enabled_for_ability(cfg.parameters, "chat_completion", mid)
    ]


def _is_chat_capable(cfg: ServerConfig) -> bool:
    """Check whether a ServerConfig supports chat completions.

    A server is chat-capable if:
      - its server_type is one of "openai", "chat", "llm", "bailian", OR
      - ``parameters.provider`` is "dashscope", OR
      - ``parameters.chat_enabled`` is true
    """
    if cfg.server_type in CHAT_SERVER_TYPES:
        return True
    if cfg.parameters.get("provider") == "dashscope":
        return True
    return bool(cfg.parameters.get("chat_enabled"))


class ChatService:
    """Routes chat completion requests to LLM backends configured as Servers."""

    def __init__(self, server_manager: ServerManager):
        self._server_manager = server_manager
        # Lazy import to avoid circular dependency
        self._selection_service = None

    @property
    def selection_service(self):
        """Get selection service (lazy initialization)."""
        if self._selection_service is None:
            from server.service.ability_selection_service import AbilitySelectionService
            self._selection_service = AbilitySelectionService(self._server_manager)
        return self._selection_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Execute a non-streaming chat completion."""
        server_cfg, model_name = self._resolve_server_and_model(request)

        logger.info(
            "chat_completion model=%s server=%s",
            model_name, server_cfg.name,
        )

        # Execute via server plugin
        result = await self._execute_via_server(
            server_cfg=server_cfg,
            model=model_name,
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            stop=request.stop,
            stream=False,
        )

        return self._convert_to_response(result, model_name)

    async def chat_completion_stream(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[ChatCompletionChunk]:
        """Execute a streaming chat completion, yielding SSE-ready chunks."""
        server_cfg, model_name = self._resolve_server_and_model(request)

        logger.info(
            "chat_completion_stream model=%s server=%s",
            model_name, server_cfg.name,
        )

        # Execute via server plugin and yield chunks
        async for chunk in self._execute_stream_via_server(
            server_cfg=server_cfg,
            model=model_name,
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            stop=request.stop,
        ):
            yield chunk

    def list_models(self) -> List[ModelInfo]:
        """Collect advertised models from all chat-capable servers."""
        models: List[ModelInfo] = []
        seen: set = set()

        for server in self._server_manager.list_servers():
            cfg = server.config
            if not cfg.enabled or not _is_chat_capable(cfg):
                continue

            owner = cfg.name

            for model_id in _advertised_chat_model_ids(cfg):
                if model_id not in seen:
                    seen.add(model_id)
                    models.append(ModelInfo(id=model_id, owned_by=owner))

        return models

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_server_and_model(
        self, request: ChatCompletionRequest
    ) -> tuple[ServerConfig, str]:
        """
        Resolve server and model using AbilitySelectionService.

        Uses the unified selection system to find the best server:model
        combination based on request.selection or backward-compatible mode.

        Returns:
            Tuple of (ServerConfig, model_name)

        Raises:
            ValueError: If no suitable server/model found
        """
        from server.service.ability_selection_service import SelectionError

        config = request.to_selection_config()

        try:
            result = self.selection_service.select(Capability.CHAT_COMPLETION, config)

            server = self._server_manager.get_server(result.server_name)
            if not server or not server.is_enabled:
                raise ValueError(
                    f"Server '{result.server_name}' not found or disabled"
                )

            logger.info(
                "Resolved selection: server=%s model=%s mode=%s reason=%s",
                result.server_name,
                result.model_name,
                result.mode_used.value,
                result.selection_reason,
            )

            return server.config, result.model_name

        except SelectionError as e:
            raise ValueError(str(e)) from e

    def _resolve_server(self, request: ChatCompletionRequest) -> ServerConfig:
        """Legacy method for backward compatibility."""
        server_cfg, _ = self._resolve_server_and_model(request)
        return server_cfg

    async def _execute_via_server(
        self,
        server_cfg: ServerConfig,
        model: str,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[List[str]] = None,
        stream: bool = False,
    ) -> TaskResult:
        """
        Execute chat completion via Server's plugin.

        Returns:
            TaskResult with the completion result in metadata
        """
        # Get the server from ServerManager
        server = self._server_manager.get_server(server_cfg.name)
        if not server:
            raise ValueError(f"Server '{server_cfg.name}' not found")

        # For bailian server, call directly instead of via plugin process
        if server_cfg.server_type == "bailian":
            return await self._execute_bailian_direct(
                server_cfg=server_cfg,
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
            )

        # Build task parameters
        task_params = {
            "model": model,
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if top_p is not None:
            task_params["top_p"] = top_p
        if stop is not None:
            task_params["stop"] = stop

        # Build metadata with server config
        task_metadata = {
            "server_config": {
                "api_key": server_cfg.api_key,
                **server_cfg.parameters,
            }
        }

        # Create FilmetoTask
        task = FilmetoTask(
            task_id=f"chat_{uuid.uuid4().hex[:12]}",
            capability=Capability.CHAT_COMPLETION,
            parameters=task_params,
            metadata=task_metadata,
        )

        # Execute via server
        result = None
        async for msg in server.execute_task(task):
            if isinstance(msg, TaskResult):
                result = msg
                break

        if result is None:
            raise RuntimeError("No result received from server")

        if result.status == "error":
            raise RuntimeError(f"Chat completion failed: {result.error_message}")

        return result

    async def _execute_bailian_direct(
        self,
        server_cfg: ServerConfig,
        model: str,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> TaskResult:
        """Execute chat completion directly via BailianServerPlugin (in-process)."""
        try:
            from server.plugins.bailian_server.main import BailianServerPlugin

            # Build parameters
            parameters = {
                "model": model,
                "messages": [m.model_dump(exclude_none=True) for m in messages],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream,
            }

            # Build server config for plugin
            server_config = {
                "api_key": server_cfg.api_key,
                **server_cfg.parameters,
            }

            # Create plugin and execute
            plugin = BailianServerPlugin()

            # Define a simple progress callback
            progress_updates = []

            def progress_callback(progress: float, message: str, metadata: dict):
                progress_updates.append({"progress": progress, "message": message, "metadata": metadata})

            task_data = {
                "task_id": f"chat_{uuid.uuid4().hex[:12]}",
                "capability": "chat_completion",
                "parameters": parameters,
                "metadata": {"server_config": server_config},
            }

            result = await plugin.execute_task(task_data, progress_callback)

            if result.get("status") == "error":
                raise RuntimeError(f"Chat completion failed: {result.get('error_message')}")

            return TaskResult(
                task_id=result.get("task_id", ""),
                status=result.get("status", "success"),
                output_files=result.get("output_files", []),
                metadata={
                    "text": result.get("metadata", {}).get("text", ""),
                    "model": result.get("metadata", {}).get("model", model),
                },
            )
        except ImportError as e:
            raise RuntimeError(f"Bailian plugin not available: {e}")

    async def _execute_stream_via_server(
        self,
        server_cfg: ServerConfig,
        model: str,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[List[str]] = None,
    ) -> AsyncIterator[ChatCompletionChunk]:
        """
        Execute streaming chat completion via Server's plugin.

        Yields ChatCompletionChunk objects.
        """
        # Get the server from ServerManager
        server = self._server_manager.get_server(server_cfg.name)
        if not server:
            raise ValueError(f"Server '{server_cfg.name}' not found")

        # Build task parameters
        task_params = {
            "model": model,
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if top_p is not None:
            task_params["top_p"] = top_p
        if stop is not None:
            task_params["stop"] = stop

        # Build metadata with server config
        task_metadata = {
            "server_config": {
                "api_key": server_cfg.api_key,
                **server_cfg.parameters,
            }
        }

        # Create FilmetoTask
        task = FilmetoTask(
            task_id=f"chat_{uuid.uuid4().hex[:12]}",
            capability=Capability.CHAT_COMPLETION,
            parameters=task_params,
            metadata=task_metadata,
        )

        # Execute via server and yield chunks
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        created = int(time.time())
        accumulated_content = ""

        async for msg in server.execute_task(task):
            if isinstance(msg, TaskProgress):
                # Extract partial content from progress
                partial = msg.metadata or {}
                if "partial_content" in partial:
                    new_content = partial["partial_content"]
                    # Calculate delta
                    delta_content = new_content[len(accumulated_content):] if accumulated_content else new_content
                    accumulated_content = new_content

                    if delta_content:
                        yield ChatCompletionChunk(
                            id=completion_id,
                            created=created,
                            model=model,
                            choices=[
                                ChatCompletionChunkChoice(
                                    index=0,
                                    delta=DeltaMessage(content=delta_content),
                                    finish_reason=None,
                                )
                            ],
                        )
            elif isinstance(msg, TaskResult):
                # Final result
                if msg.status == "error":
                    raise RuntimeError(f"Chat completion failed: {msg.error_message}")

                # Check if there's remaining content in the result
                final_text = msg.metadata.get("text", "")
                delta_content = final_text[len(accumulated_content):] if accumulated_content else final_text

                if delta_content:
                    yield ChatCompletionChunk(
                        id=completion_id,
                        created=created,
                        model=model,
                        choices=[
                            ChatCompletionChunkChoice(
                                index=0,
                                delta=DeltaMessage(content=delta_content),
                                finish_reason="stop",
                            )
                        ],
                    )
                else:
                    # Send final chunk with finish_reason
                    yield ChatCompletionChunk(
                        id=completion_id,
                        created=created,
                        model=model,
                        choices=[
                            ChatCompletionChunkChoice(
                                index=0,
                                delta=DeltaMessage(),
                                finish_reason="stop",
                            )
                        ],
                    )

    def _convert_to_response(
        self, result: TaskResult, model: str
    ) -> ChatCompletionResponse:
        """Convert TaskResult to ChatCompletionResponse."""
        # Extract text from metadata
        text = result.metadata.get("text", "") if result.metadata else ""

        # Extract usage if available
        usage_dict = result.metadata.get("usage", {}) if result.metadata else {}
        usage = UsageInfo(
            prompt_tokens=usage_dict.get("prompt_tokens", 0),
            completion_tokens=usage_dict.get("completion_tokens", 0),
            total_tokens=usage_dict.get("total_tokens", 0),
        )

        return ChatCompletionResponse(
            id=result.task_id,
            created=int(time.time()),
            model=model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=text,
                    ),
                    finish_reason="stop",
                )
            ],
            usage=usage,
        )