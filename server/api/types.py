"""
FilmetoApi Type Definitions

Defines all data structures used in the Filmeto API system.
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class Ability(str, Enum):
    """Enumeration of AI abilities (task / plugin kinds)."""
    TEXT2IMAGE = "text2image"      # Text to image generation
    IMAGE2IMAGE = "image2image"    # Image to image transformation
    IMAGE2VIDEO = "image2video"    # Image to video animation
    TEXT2VIDEO = "text2video"      # Text to video generation
    SPEAK2VIDEO = "speak2video"    # Speech to video (avatar)
    TEXT2SPEAK = "text2speak"      # Text to speech synthesis
    TEXT2MUSIC = "text2music"      # Text to music generation
    CHAT_COMPLETION = "chat_completion"  # LLM chat completion


class ResourceType(str, Enum):
    """Type of resource input"""
    LOCAL_PATH = "local_path"
    REMOTE_URL = "remote_url"
    BASE64 = "base64"


class ProgressType(str, Enum):
    """Type of progress update"""
    STARTED = "started"
    PROGRESS = "progress"
    HEARTBEAT = "heartbeat"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ResourceInput:
    """
    Resource input supporting multiple formats.

    Attributes:
        type: Type of resource (local_path, remote_url, base64)
        data: The actual data (path, URL, or base64 string)
        mime_type: MIME type of the resource (e.g., "image/png", "video/mp4")
        metadata: Optional metadata about the resource
    """
    type: ResourceType
    data: str
    mime_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type.value,
            "data": self.data,
            "mime_type": self.mime_type,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceInput':
        """Create from dictionary"""
        return cls(
            type=ResourceType(data["type"]),
            data=data["data"],
            mime_type=data["mime_type"],
            metadata=data.get("metadata", {})
        )


@dataclass
class ResourceOutput:
    """
    Output resource with metadata.

    Attributes:
        type: Type of resource (image, video, audio)
        path: Local path to the file
        url: Optional URL if uploaded to remote storage
        mime_type: MIME type of the resource
        size: File size in bytes
        metadata: Additional metadata (dimensions, duration, etc.)
    """
    type: str
    path: str
    mime_type: str
    size: int
    url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type,
            "path": self.path,
            "url": self.url,
            "mime_type": self.mime_type,
            "size": self.size,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceOutput':
        """Create from dictionary"""
        return cls(
            type=data["type"],
            path=data["path"],
            mime_type=data["mime_type"],
            size=data["size"],
            url=data.get("url"),
            metadata=data.get("metadata", {})
        )


@dataclass
class FilmetoTask:
    """
    Task definition for Filmeto API.

    Attributes:
        task_id: Unique task identifier
        ability: AI ability to execute
        server_name: Server instance name to use (optional if selection provided)
        model_name: Model name to use (optional)
        parameters: Ability-specific parameters
        resources: Input resources (images, videos, etc.)
        created_at: Task creation timestamp
        timeout: Timeout in seconds
        metadata: Additional metadata
        selection: Selection configuration for auto server/model selection
    """
    ability: Ability
    parameters: Dict[str, Any]
    server_name: Optional[str] = None
    model_name: Optional[str] = None
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    resources: List[ResourceInput] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    timeout: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)
    selection: Optional[SelectionConfig] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "task_id": self.task_id,
            "ability": self.ability.value,
            "parameters": self.parameters,
            "resources": [r.to_dict() for r in self.resources],
            "created_at": self.created_at.isoformat(),
            "timeout": self.timeout,
            "metadata": self.metadata
        }
        if self.server_name:
            result["server_name"] = self.server_name
        if self.model_name:
            result["model_name"] = self.model_name
        if self.selection:
            result["selection"] = {
                "mode": self.selection.mode.value,
                "server": self.selection.server,
                "model": self.selection.model,
                "tags": self.selection.tags,
                "min_priority": self.selection.min_priority,
            }
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilmetoTask':
        """Create from dictionary"""
        selection = None
        if data.get("selection"):
            selection = SelectionConfig.from_dict(data["selection"])

        _abil = data.get("ability") or data.get("capability")
        if _abil is None:
            raise KeyError("FilmetoTask requires 'ability' (or legacy 'capability')")
        return cls(
            task_id=data.get("task_id", str(uuid.uuid4())),
            ability=Ability(str(_abil)),
            server_name=data.get("server_name"),
            model_name=data.get("model_name"),
            parameters=data["parameters"],
            resources=[ResourceInput.from_dict(r) for r in data.get("resources", [])],
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            timeout=data.get("timeout", 300),
            metadata=data.get("metadata", {}),
            selection=selection,
        )

    def get_selection_config(self) -> SelectionConfig:
        """
        Get selection configuration.

        If selection is explicitly set, return it.
        Otherwise, infer from server_name and model_name for backward compatibility.
        """
        if self.selection:
            return self.selection

        # Backward compatibility: infer mode from server_name/model_name
        if self.server_name and self.model_name:
            return SelectionConfig.exact(self.server_name, self.model_name)
        elif self.server_name:
            return SelectionConfig.server_only(self.server_name)
        else:
            return SelectionConfig.auto()

    def resolve_selection(self, result: 'SelectionResult') -> None:
        """
        Resolve selection by updating server_name and model_name from result.

        Args:
            result: Selection result from AbilitySelectionService
        """
        self.server_name = result.server_name
        self.model_name = result.model_name

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate task structure.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # server_name is now optional - can be resolved via selection
        # Only validate if explicitly set to empty string
        if self.server_name is not None and self.server_name == "":
            return False, "Server name cannot be empty string"

        if not self.parameters:
            return False, "Parameters are required"

        # Validate resources
        for resource in self.resources:
            if not resource.data:
                return False, "Resource data cannot be empty"
            if not resource.mime_type:
                return False, "Resource mime_type is required"

        # Ability-specific validation
        if self.ability == Ability.TEXT2IMAGE:
            if "prompt" not in self.parameters:
                return False, "TEXT2IMAGE requires 'prompt' parameter"
        elif self.ability == Ability.IMAGE2IMAGE:
            if "prompt" not in self.parameters:
                return False, "IMAGE2IMAGE requires 'prompt' parameter"
            if not self.resources:
                return False, "IMAGE2IMAGE requires at least one input image"
        elif self.ability == Ability.IMAGE2VIDEO:
            if not self.resources:
                return False, "IMAGE2VIDEO requires at least one input image"
        elif self.ability == Ability.TEXT2VIDEO:
            if "prompt" not in self.parameters:
                return False, "TEXT2VIDEO requires 'prompt' parameter"
        elif self.ability == Ability.SPEAK2VIDEO:
            if not self.resources:
                return False, "SPEAK2VIDEO requires audio input"
        elif self.ability == Ability.TEXT2SPEAK:
            if "text" not in self.parameters:
                return False, "TEXT2SPEAK requires 'text' parameter"
        elif self.ability == Ability.TEXT2MUSIC:
            if "prompt" not in self.parameters:
                return False, "TEXT2MUSIC requires 'prompt' parameter"

        return True, None


@dataclass
class TaskProgress:
    """
    Progress update during task execution.

    Attributes:
        task_id: Task identifier
        type: Type of progress update
        percent: Progress percentage (0-100)
        message: Human-readable progress message
        timestamp: Update timestamp
        data: Additional progress data
    """
    task_id: str
    type: ProgressType
    percent: float
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "type": self.type.value,
            "percent": self.percent,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskProgress':
        """Create from dictionary"""
        return cls(
            task_id=data["task_id"],
            type=ProgressType(data["type"]),
            percent=data["percent"],
            message=data["message"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            data=data.get("data", {})
        )


@dataclass
class TaskResult:
    """
    Final result of task execution.

    Attributes:
        task_id: Task identifier
        status: Execution status (success or error)
        output_files: List of generated file paths
        output_resources: List of processed resources with metadata
        error_message: Error message if failed
        execution_time: Execution time in seconds
        metadata: Additional result metadata
    """
    task_id: str
    status: str
    output_files: List[str] = field(default_factory=list)
    output_resources: List[ResourceOutput] = field(default_factory=list)
    error_message: str = ""
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "output_files": self.output_files,
            "output_resources": [r.to_dict() for r in self.output_resources],
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskResult':
        """Create from dictionary"""
        return cls(
            task_id=data["task_id"],
            status=data["status"],
            output_files=data.get("output_files", []),
            output_resources=[ResourceOutput.from_dict(r) for r in data.get("output_resources", [])],
            error_message=data.get("error_message", ""),
            execution_time=data.get("execution_time", 0.0),
            metadata=data.get("metadata", {})
        )

    def get_image_path(self) -> Optional[str]:
        """Get the first image file from output files"""
        for file_path in self.output_files:
            if file_path.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                return file_path
        return None

    def get_video_path(self) -> Optional[str]:
        """Get the first video file from output files"""
        for file_path in self.output_files:
            if file_path.endswith(('.mp4', '.mov', '.avi')):
                return file_path
        return None

    def get_audio_path(self) -> Optional[str]:
        """Get the first audio file from output files"""
        for file_path in self.output_files:
            if file_path.endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                return file_path
        return None


# --- Retry policy ---------------------------------------------------------

class RetryStrategy(str, Enum):
    """Backoff strategy between retry attempts."""
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"


@dataclass
class RetryPolicy:
    """
    Controls how a failed server execution is retried.

    Attributes:
        max_retries: Maximum number of retry attempts (0 = no retry).
        strategy: Backoff strategy between attempts.
        base_delay: Base delay in seconds for the first retry.
        max_delay: Upper-bound delay in seconds.
        jitter: If True, add random jitter (0–50 % of delay) to avoid
                thundering-herd on shared backends.
        retryable_codes: Set of TaskError.code values that are eligible for
                         retry.  Errors whose code is not listed here will
                         propagate immediately.
    """
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True
    retryable_codes: frozenset = field(default_factory=lambda: frozenset({
        "PLUGIN_EXECUTION_ERROR",
        "TIMEOUT_ERROR",
        "RESOURCE_PROCESSING_ERROR",
    }))

    def compute_delay(self, attempt: int) -> float:
        """Return the delay in seconds before *attempt* (0-indexed)."""
        import random as _random
        if self.strategy == RetryStrategy.NONE:
            return 0.0
        if self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        else:
            delay = self.base_delay * (2 ** attempt)
        delay = min(delay, self.max_delay)
        if self.jitter:
            delay += _random.uniform(0, delay * 0.5)
        return delay

    def is_retryable(self, error: Exception) -> bool:
        """Check whether *error* should trigger a retry."""
        if isinstance(error, TaskError):
            return error.code in self.retryable_codes
        return isinstance(error, (OSError, asyncio.TimeoutError))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RetryPolicy':
        strategy_val = data.get("strategy", "exponential")
        return cls(
            max_retries=data.get("max_retries", 3),
            strategy=RetryStrategy(strategy_val),
            base_delay=data.get("base_delay", 1.0),
            max_delay=data.get("max_delay", 60.0),
            jitter=data.get("jitter", True),
        )


# Error types for API
class TaskError(Exception):
    """Base exception for task errors"""
    def __init__(self, code: str, message: str, details: Dict[str, Any] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details
        }


class ValidationError(TaskError):
    """Task validation error"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__("VALIDATION_ERROR", message, details)


class ServerNotFoundError(TaskError):
    """Server not found error"""
    def __init__(self, server_name: str):
        super().__init__(
            "SERVER_NOT_FOUND",
            f"Server '{server_name}' not found",
            {"server_name": server_name}
        )


class ServerExecutionError(TaskError):
    """Server execution error"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__("SERVER_EXECUTION_ERROR", message, details)


class ResourceProcessingError(TaskError):
    """Resource processing error"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__("RESOURCE_PROCESSING_ERROR", message, details)


class TimeoutError(TaskError):
    """Task timeout error"""
    def __init__(self, task_id: str, timeout: int):
        super().__init__(
            "TIMEOUT_ERROR",
            f"Task '{task_id}' exceeded timeout of {timeout} seconds",
            {"task_id": task_id, "timeout": timeout}
        )


# --- Selection Types --------------------------------------------------------

class SelectionMode(str, Enum):
    """Service/model selection mode."""
    AUTO = "auto"                  # Auto select both server and model
    SERVER_ONLY = "server_only"   # Specify server, auto select model
    EXACT = "exact"               # Exact server:model specification


@dataclass
class SelectionConfig:
    """
    Unified selection configuration.

    Attributes:
        mode: Selection mode (AUTO, SERVER_ONLY, EXACT)
        server: Server name (required for SERVER_ONLY and EXACT modes)
        model: Model name (required for EXACT mode, optional for AUTO/SERVER_ONLY)
        tags: Tag filters for model selection
        min_priority: Minimum priority threshold
    """
    mode: SelectionMode = SelectionMode.AUTO
    server: Optional[str] = None
    model: Optional[str] = None
    tags: Optional[List[str]] = None
    min_priority: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {"mode": self.mode.value}
        if self.server is not None:
            result["server"] = self.server
        if self.model is not None:
            result["model"] = self.model
        if self.tags is not None:
            result["tags"] = self.tags
        if self.min_priority is not None:
            result["min_priority"] = self.min_priority
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SelectionConfig':
        """Create from dictionary."""
        mode_str = data.get("mode", "auto")
        return cls(
            mode=SelectionMode(mode_str),
            server=data.get("server"),
            model=data.get("model"),
            tags=data.get("tags"),
            min_priority=data.get("min_priority"),
        )

    @classmethod
    def auto(cls, tags: Optional[List[str]] = None, min_priority: Optional[int] = None) -> 'SelectionConfig':
        """Create AUTO mode config."""
        return cls(mode=SelectionMode.AUTO, tags=tags, min_priority=min_priority)

    @classmethod
    def server_only(cls, server: str, model: Optional[str] = None,
                    tags: Optional[List[str]] = None) -> 'SelectionConfig':
        """Create SERVER_ONLY mode config."""
        return cls(mode=SelectionMode.SERVER_ONLY, server=server, model=model, tags=tags)

    @classmethod
    def exact(cls, server: str, model: str) -> 'SelectionConfig':
        """Create EXACT mode config."""
        return cls(mode=SelectionMode.EXACT, server=server, model=model)


@dataclass
class SelectionResult:
    """
    Selection result.

    Attributes:
        server_name: Selected server name
        model_name: Selected model name
        ability_type: Ability type
        key: Combined key in "server:model" format
        mode_used: Selection mode that was used
        instance: The selected AbilityInstance
        candidates_count: Number of candidates considered
        selection_reason: Human-readable reason for selection
    """
    server_name: str
    model_name: str
    ability_type: 'Ability'
    key: str
    mode_used: SelectionMode
    instance: 'AbilityInstance'
    candidates_count: int = 0
    selection_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "server_name": self.server_name,
            "model_name": self.model_name,
            "ability_type": self.ability_type.value,
            "key": self.key,
            "mode_used": self.mode_used.value,
            "candidates_count": self.candidates_count,
            "selection_reason": self.selection_reason,
            "instance": self.instance.to_dict() if self.instance else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SelectionResult':
        """Create from dictionary."""
        instance_data = data.get("instance")
        instance = AbilityInstance.from_dict(instance_data) if instance_data else None
        _at = data.get("ability_type") or data.get("capability_type")
        return cls(
            server_name=data["server_name"],
            model_name=data["model_name"],
            ability_type=Ability(str(_at)),
            key=data["key"],
            mode_used=SelectionMode(data["mode_used"]),
            instance=instance,
            candidates_count=data.get("candidates_count", 0),
            selection_reason=data.get("selection_reason", ""),
        )


# --- Ability discovery types ---------------------------------------------

@dataclass
class ModelPricing:
    """
    Pricing information for a model.

    Supports different pricing models:
    - Per-call: Fixed cost per API call
    - Per-token: Cost per input/output token (for LLMs)
    - Per-second: Cost per second of processing (for video/audio)
    - Per-image: Cost per image generated

    All prices are in USD.
    """
    # Per-call pricing
    per_call: Optional[float] = None  # Fixed cost per call

    # Token-based pricing (for LLMs)
    per_input_token: Optional[float] = None  # Cost per 1K input tokens
    per_output_token: Optional[float] = None  # Cost per 1K output tokens

    # Duration-based pricing (for video/audio)
    per_second: Optional[float] = None  # Cost per second of output

    # Image-based pricing
    per_image: Optional[float] = None  # Cost per image generated

    # Custom unit pricing
    custom_unit: Optional[str] = None  # Unit name (e.g., "per_1k_characters")
    custom_rate: Optional[float] = None  # Rate per custom unit

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {}
        if self.per_call is not None:
            result["per_call"] = self.per_call
        if self.per_input_token is not None:
            result["per_input_token"] = self.per_input_token
        if self.per_output_token is not None:
            result["per_output_token"] = self.per_output_token
        if self.per_second is not None:
            result["per_second"] = self.per_second
        if self.per_image is not None:
            result["per_image"] = self.per_image
        if self.custom_unit is not None:
            result["custom_unit"] = self.custom_unit
        if self.custom_rate is not None:
            result["custom_rate"] = self.custom_rate
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelPricing':
        """Create from dictionary"""
        return cls(
            per_call=data.get("per_call"),
            per_input_token=data.get("per_input_token"),
            per_output_token=data.get("per_output_token"),
            per_second=data.get("per_second"),
            per_image=data.get("per_image"),
            custom_unit=data.get("custom_unit"),
            custom_rate=data.get("custom_rate"),
        )

    def estimate_cost(self, **kwargs) -> Optional[float]:
        """
        Estimate cost for a given usage.

        Args:
            **kwargs: Usage parameters based on pricing type
                - num_calls: Number of API calls
                - input_tokens: Number of input tokens
                - output_tokens: Number of output tokens
                - seconds: Duration in seconds
                - num_images: Number of images

        Returns:
            Estimated cost in USD, or None if cannot estimate
        """
        total = 0.0

        if self.per_call is not None and "num_calls" in kwargs:
            total += self.per_call * kwargs["num_calls"]

        if self.per_input_token is not None and "input_tokens" in kwargs:
            total += self.per_input_token * (kwargs["input_tokens"] / 1000)

        if self.per_output_token is not None and "output_tokens" in kwargs:
            total += self.per_output_token * (kwargs["output_tokens"] / 1000)

        if self.per_second is not None and "seconds" in kwargs:
            total += self.per_second * kwargs["seconds"]

        if self.per_image is not None and "num_images" in kwargs:
            total += self.per_image * kwargs["num_images"]

        return total if total > 0 else None


@dataclass
class ModelInfo:
    """
    Information about a specific model.

    Models are the specific implementations within an ability.
    Each server/plugin can support multiple models for an ability.

    Attributes:
        name: Model identifier (e.g., "wanx2.1-t2i-turbo", "qwen-max")
        display_name: Human-readable name for UI display
        description: Short description of the model
        detailed_description: Detailed description with features and use cases
        ability: Which ability this model belongs to
        provider: Provider name (e.g., "Alibaba", "OpenAI")
        version: Model version string
        tags: Tags for filtering (e.g., ["fast", "high-quality"])
        specs: Technical specifications
            - max_resolution: Maximum output resolution (for image models)
            - max_duration: Maximum output duration in seconds (for video/audio)
            - context_length: Maximum context length (for LLMs)
            - supports_vision: Whether the model supports image input
            - supports_audio: Whether the model supports audio input
        pricing: Pricing information
        is_default: Whether this is the default model for the ability
        is_available: Whether this model is currently available
        metadata: Additional metadata
    """
    name: str
    display_name: str
    description: str
    ability: 'Ability'
    provider: str = ""
    version: str = ""
    detailed_description: str = ""
    tags: List[str] = field(default_factory=list)
    specs: Dict[str, Any] = field(default_factory=dict)
    pricing: Optional[ModelPricing] = None
    is_default: bool = False
    is_available: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "ability": self.ability.value,
            "provider": self.provider,
            "version": self.version,
            "detailed_description": self.detailed_description,
            "tags": self.tags,
            "specs": self.specs,
            "pricing": self.pricing.to_dict() if self.pricing else None,
            "is_default": self.is_default,
            "is_available": self.is_available,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelInfo':
        """Create from dictionary"""
        pricing = None
        if data.get("pricing"):
            pricing = ModelPricing.from_dict(data["pricing"])

        _ab = data.get("ability") or data.get("capability")
        return cls(
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            description=data["description"],
            ability=Ability(str(_ab)),
            provider=data.get("provider", ""),
            version=data.get("version", ""),
            detailed_description=data.get("detailed_description", ""),
            tags=data.get("tags", []),
            specs=data.get("specs", {}),
            pricing=pricing,
            is_default=data.get("is_default", False),
            is_available=data.get("is_available", True),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AbilityInstance:
    """
    Represents a specific ability instance (server:model combination).

    This is the basic unit for LLM service selection, containing complete
    description information for the LLM to understand the characteristics
    and use cases of this ability instance.

    Attributes:
        key: Unique identifier in "server:model" format
        server_name: Server instance name (e.g., "bailian-prod", "comfyui-local")
        model_name: Model name (e.g., "wanx2.1-t2i-turbo", "sd-xl")
        ability_type: Ability type (Ability enum)
        description: Short description (1-2 sentences)
        detailed_description: Detailed description with features, use cases, etc.
        tags: Tags for filtering (e.g., ["fast", "high-quality", "chinese-optimized"])
        specs: Technical specifications dict
        pricing: Pricing information (copied from model info)
        priority: Priority for recommendation (higher = more recommended)
        is_available: Whether this instance is currently available
        metadata: Additional metadata
    """
    key: str
    server_name: str
    model_name: str
    ability_type: 'Ability'
    description: str
    detailed_description: str = ""
    tags: List[str] = field(default_factory=list)
    specs: Dict[str, Any] = field(default_factory=dict)
    pricing: Optional[ModelPricing] = None
    priority: int = 0
    is_available: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "key": self.key,
            "server_name": self.server_name,
            "model_name": self.model_name,
            "ability_type": self.ability_type.value,
            "description": self.description,
            "detailed_description": self.detailed_description,
            "tags": self.tags,
            "specs": self.specs,
            "pricing": self.pricing.to_dict() if self.pricing else None,
            "priority": self.priority,
            "is_available": self.is_available,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AbilityInstance':
        """Create from dictionary"""
        pricing = None
        if data.get("pricing"):
            pricing = ModelPricing.from_dict(data["pricing"])

        _at = data.get("ability_type") or data.get("capability_type")
        return cls(
            key=data["key"],
            server_name=data["server_name"],
            model_name=data["model_name"],
            ability_type=Ability(str(_at)),
            description=data["description"],
            detailed_description=data.get("detailed_description", ""),
            tags=data.get("tags", []),
            specs=data.get("specs", {}),
            pricing=pricing,
            priority=data.get("priority", 0),
            is_available=data.get("is_available", True),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_model_info(cls, server_name: str, model_info: ModelInfo) -> 'AbilityInstance':
        """
        Create AbilityInstance from ModelInfo.

        Args:
            server_name: Server instance name
            model_info: Model information

        Returns:
            AbilityInstance with key format "server_name:model_name"
        """
        return cls(
            key=f"{server_name}:{model_info.name}",
            server_name=server_name,
            model_name=model_info.name,
            ability_type=model_info.ability,
            description=model_info.description,
            detailed_description=model_info.detailed_description,
            tags=model_info.tags,
            specs=model_info.specs,
            pricing=model_info.pricing,
            priority=10 if model_info.is_default else 0,
            is_available=model_info.is_available,
            metadata=model_info.metadata,
        )


@dataclass
class AbilityGroup:
    """
    Group of ability instances by ability type.

    Used to display all available options for a specific ability.

    Attributes:
        ability_type: Ability type enum
        ability_name: Human-readable ability name
        description: Description of this ability type
        instances: List of available ability instances (server:model combinations)
        models: List of unique models available for this ability
    """
    ability_type: 'Ability'
    ability_name: str
    description: str
    instances: List[AbilityInstance] = field(default_factory=list)
    models: List[ModelInfo] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "ability_type": self.ability_type.value,
            "ability_name": self.ability_name,
            "description": self.description,
            "instances": [inst.to_dict() for inst in self.instances],
            "models": [model.to_dict() for model in self.models],
            "total_instances": len(self.instances),
            "total_models": len(self.models),
        }