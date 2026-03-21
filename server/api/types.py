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


class ToolType(str, Enum):
    """Enumeration of supported tool types"""
    TEXT2IMAGE = "text2image"      # Text to image generation
    IMAGE2IMAGE = "image2image"    # Image to image transformation
    IMAGE2VIDEO = "image2video"    # Image to video animation
    TEXT2VIDEO = "text2video"      # Text to video generation
    SPEAK2VIDEO = "speak2video"    # Speech to video (avatar)
    TEXT2SPEAK = "text2speak"      # Text to speech synthesis
    TEXT2MUSIC = "text2music"      # Text to music generation


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
        tool_name: Tool to execute
        plugin_name: Server plugin name to use
        parameters: Tool-specific parameters
        resources: Input resources (images, videos, etc.)
        created_at: Task creation timestamp
        timeout: Timeout in seconds
        metadata: Additional metadata
    """
    tool_name: ToolType
    plugin_name: str
    parameters: Dict[str, Any]
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    resources: List[ResourceInput] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    timeout: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "tool_name": self.tool_name.value,
            "plugin_name": self.plugin_name,
            "parameters": self.parameters,
            "resources": [r.to_dict() for r in self.resources],
            "created_at": self.created_at.isoformat(),
            "timeout": self.timeout,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilmetoTask':
        """Create from dictionary"""
        return cls(
            task_id=data.get("task_id", str(uuid.uuid4())),
            tool_name=ToolType(data["tool_name"]),
            plugin_name=data["plugin_name"],
            parameters=data["parameters"],
            resources=[ResourceInput.from_dict(r) for r in data.get("resources", [])],
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            timeout=data.get("timeout", 300),
            metadata=data.get("metadata", {})
        )
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate task structure.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.plugin_name:
            return False, "Plugin name is required"
        
        if not self.parameters:
            return False, "Parameters are required"
        
        # Validate resources
        for resource in self.resources:
            if not resource.data:
                return False, "Resource data cannot be empty"
            if not resource.mime_type:
                return False, "Resource mime_type is required"
        
        # Tool-specific validation
        if self.tool_name == ToolType.TEXT2IMAGE:
            if "prompt" not in self.parameters:
                return False, "TEXT2IMAGE requires 'prompt' parameter"
        elif self.tool_name == ToolType.IMAGE2IMAGE:
            if "prompt" not in self.parameters:
                return False, "IMAGE2IMAGE requires 'prompt' parameter"
            if not self.resources:
                return False, "IMAGE2IMAGE requires at least one input image"
        elif self.tool_name == ToolType.IMAGE2VIDEO:
            if not self.resources:
                return False, "IMAGE2VIDEO requires at least one input image"
        elif self.tool_name == ToolType.TEXT2VIDEO:
            if "prompt" not in self.parameters:
                return False, "TEXT2VIDEO requires 'prompt' parameter"
        elif self.tool_name == ToolType.SPEAK2VIDEO:
            if not self.resources:
                return False, "SPEAK2VIDEO requires audio input"
        elif self.tool_name == ToolType.TEXT2SPEAK:
            if "text" not in self.parameters:
                return False, "TEXT2SPEAK requires 'text' parameter"
        elif self.tool_name == ToolType.TEXT2MUSIC:
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


class PluginNotFoundError(TaskError):
    """Plugin not found error"""
    def __init__(self, plugin_name: str):
        super().__init__(
            "PLUGIN_NOT_FOUND",
            f"Plugin '{plugin_name}' not found",
            {"plugin_name": plugin_name}
        )


class PluginExecutionError(TaskError):
    """Plugin execution error"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__("PLUGIN_EXECUTION_ERROR", message, details)


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
