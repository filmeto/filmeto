"""
OpenAI-compatible Chat Completion Types

Pydantic models following the OpenAI Chat Completions API specification.
These types allow Filmeto to act as an OpenAI-compatible gateway, routing
requests to different LLM backends based on server configuration.
"""

import time
import uuid
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request types
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """A single message in a chat conversation."""
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[Union[str, List[Dict[str, Any]]]] = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class FunctionDefinition(BaseModel):
    """Function definition for tool use."""
    name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class ToolDefinition(BaseModel):
    """Tool definition for function calling."""
    type: Literal["function"] = "function"
    function: FunctionDefinition


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""
    model: Optional[str] = None  # Now optional for AUTO selection mode
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: int = 1
    stream: bool = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: float = 0
    frequency_penalty: float = 0
    tools: Optional[List[ToolDefinition]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    user: Optional[str] = None

    server: Optional[str] = Field(
        None,
        description="Filmeto extension: explicit target server name for routing"
    )

    selection: Optional[Dict[str, Any]] = Field(
        None,
        description="Filmeto extension: selection configuration for auto server/model selection"
    )

    def to_selection_config(self) -> 'SelectionConfig':
        """
        Convert request to SelectionConfig.

        Backward compatibility:
        - server + model -> EXACT mode
        - server only -> SERVER_ONLY mode
        - model only -> AUTO mode (search by model)
        - neither -> AUTO mode
        """
        from server.api.types import SelectionConfig, SelectionMode

        if self.selection:
            return SelectionConfig.from_dict(self.selection)

        # Backward compatibility: infer mode from server/model
        if self.server and self.model:
            return SelectionConfig.exact(self.server, self.model)
        elif self.server:
            return SelectionConfig.server_only(self.server, self.model)
        elif self.model:
            # Model specified but no server - use AUTO with model preference
            return SelectionConfig(mode=SelectionMode.AUTO, model=self.model)
        else:
            return SelectionConfig.auto()


# ---------------------------------------------------------------------------
# Non-streaming response types
# ---------------------------------------------------------------------------

class ChatCompletionChoice(BaseModel):
    """A single completion choice."""
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class UsageInfo(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChoice]
    usage: UsageInfo = Field(default_factory=UsageInfo)
    filmeto_server: Optional[str] = Field(
        None,
        description="Filmeto extension: server name that executed the completion",
    )
    filmeto_model: Optional[str] = Field(
        None,
        description="Filmeto extension: model id actually used by the provider",
    )


# ---------------------------------------------------------------------------
# Streaming response types
# ---------------------------------------------------------------------------

class DeltaMessage(BaseModel):
    """Incremental message content in a streaming chunk."""
    role: Optional[str] = None
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatCompletionChunkChoice(BaseModel):
    """A single choice within a streaming chunk."""
    index: int
    delta: DeltaMessage
    finish_reason: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    """OpenAI-compatible streaming chunk."""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionChunkChoice]
    filmeto_server: Optional[str] = Field(
        None,
        description="Filmeto extension: server name that executed the completion",
    )
    filmeto_model: Optional[str] = Field(
        None,
        description="Filmeto extension: model id actually used by the provider",
    )


# ---------------------------------------------------------------------------
# Model listing types
# ---------------------------------------------------------------------------

class ModelInfo(BaseModel):
    """Information about an available model."""
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "filmeto"


class ModelListResponse(BaseModel):
    """OpenAI-compatible model list response."""
    object: str = "list"
    data: List[ModelInfo]
