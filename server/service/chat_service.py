"""
Chat Completion Service

Routes OpenAI-compatible chat completion requests to configured LLM backends.
Each backend is represented as a Server with server_type set to one of
"openai", "chat", or "llm".  The actual LLM call is delegated to LiteLLM,
which handles provider-specific differences (OpenAI, DashScope, Anthropic,
Azure, Ollama, etc.) transparently.

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

import litellm

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
from server.api.types import Capability, SelectionConfig, SelectionMode

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
        messages = [m.model_dump(exclude_none=True) for m in request.messages]
        params = self._build_litellm_params(server_cfg, request, model_name, stream=False)

        logger.info(
            "chat_completion model=%s server=%s",
            model_name, server_cfg.name,
        )

        response = await litellm.acompletion(messages=messages, **params)
        return self._to_response(response, model_name)

    async def chat_completion_stream(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[ChatCompletionChunk]:
        """Execute a streaming chat completion, yielding SSE-ready chunks."""
        server_cfg, model_name = self._resolve_server_and_model(request)
        messages = [m.model_dump(exclude_none=True) for m in request.messages]
        params = self._build_litellm_params(server_cfg, request, model_name, stream=True)

        logger.info(
            "chat_completion_stream model=%s server=%s",
            model_name, server_cfg.name,
        )

        response = await litellm.acompletion(messages=messages, **params)

        completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        created = int(time.time())

        async for chunk in response:
            delta_data: dict = {}
            finish_reason = None

            if hasattr(chunk, "choices") and chunk.choices:
                choice = chunk.choices[0]
                delta = getattr(choice, "delta", None)
                if delta:
                    if getattr(delta, "role", None):
                        delta_data["role"] = delta.role
                    if getattr(delta, "content", None) is not None:
                        delta_data["content"] = delta.content
                    if getattr(delta, "tool_calls", None):
                        delta_data["tool_calls"] = [
                            tc.model_dump() if hasattr(tc, "model_dump") else tc
                            for tc in delta.tool_calls
                        ]
                finish_reason = getattr(choice, "finish_reason", None)

            yield ChatCompletionChunk(
                id=completion_id,
                created=created,
                model=model_name,
                choices=[
                    ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaMessage(**delta_data),
                        finish_reason=finish_reason,
                    )
                ],
            )

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

    @staticmethod
    def _build_litellm_params(
        server_cfg: ServerConfig,
        request: ChatCompletionRequest,
        model_name: str,
        *,
        stream: bool = False,
    ) -> dict:
        """Translate ServerConfig + request into litellm.acompletion kwargs."""
        sp = server_cfg.parameters
        params: dict = {"model": model_name, "stream": stream}

        # API key: prefer plugin-specific key (e.g. dashscope_api_key),
        # fall back to server-level api_key.
        api_key = sp.get("dashscope_api_key") or server_cfg.api_key
        if api_key:
            params["api_key"] = api_key

        # Endpoint: prefer plugin-specific chat endpoint,
        # fall back to server-level endpoint.
        endpoint = sp.get("dashscope_endpoint") or server_cfg.endpoint
        if endpoint:
            params["base_url"] = endpoint
            params["api_base"] = endpoint

        provider = sp.get("provider")
        if provider and provider != "openai":
            if not model_name.startswith(f"{provider}/"):
                params["model"] = f"{provider}/{model_name}"

        if request.temperature is not None:
            params["temperature"] = request.temperature
        elif "temperature" in sp:
            params["temperature"] = sp["temperature"]

        if request.top_p is not None:
            params["top_p"] = request.top_p
        if request.max_tokens is not None:
            params["max_tokens"] = request.max_tokens
        if request.stop:
            params["stop"] = request.stop
        if request.n != 1:
            params["n"] = request.n
        if request.presence_penalty:
            params["presence_penalty"] = request.presence_penalty
        if request.frequency_penalty:
            params["frequency_penalty"] = request.frequency_penalty
        if request.user:
            params["user"] = request.user

        if request.tools:
            params["tools"] = [t.model_dump() for t in request.tools]
        if request.tool_choice is not None:
            params["tool_choice"] = request.tool_choice

        extra = sp.get("litellm_params")
        if isinstance(extra, dict):
            params.update(extra)

        return params

    @staticmethod
    def _to_response(
        litellm_response, model: str
    ) -> ChatCompletionResponse:
        """Convert a litellm ModelResponse to an OpenAI-compatible response."""
        choices = []
        for i, c in enumerate(litellm_response.choices):
            msg = c.message
            tool_calls_raw = getattr(msg, "tool_calls", None)
            tool_calls = None
            if tool_calls_raw:
                tool_calls = [
                    tc.model_dump() if hasattr(tc, "model_dump") else tc
                    for tc in tool_calls_raw
                ]

            choices.append(
                ChatCompletionChoice(
                    index=i,
                    message=ChatMessage(
                        role=msg.role,
                        content=getattr(msg, "content", None),
                        tool_calls=tool_calls,
                    ),
                    finish_reason=c.finish_reason,
                )
            )

        usage_obj = getattr(litellm_response, "usage", None)
        usage = UsageInfo(
            prompt_tokens=getattr(usage_obj, "prompt_tokens", 0),
            completion_tokens=getattr(usage_obj, "completion_tokens", 0),
            total_tokens=getattr(usage_obj, "total_tokens", 0),
        ) if usage_obj else UsageInfo()

        return ChatCompletionResponse(
            id=getattr(
                litellm_response, "id",
                f"chatcmpl-{uuid.uuid4().hex[:12]}"
            ),
            created=getattr(litellm_response, "created", int(time.time())),
            model=model,
            choices=choices,
            usage=usage,
        )
