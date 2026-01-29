"""
Structure content module for Filmeto agent system.
Defines the StructureContent class hierarchy for structured message content.
"""
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
import uuid
from enum import Enum
from agent.chat.agent_chat_types import ContentType


class ContentStatus(str, Enum):
    """Status of content during its lifecycle."""
    CREATING = "creating"      # Content is being created
    UPDATING = "updating"      # Content is being updated
    COMPLETED = "completed"    # Content is completed
    FAILED = "failed"          # Content creation/update failed


@dataclass
class StructureContent:
    """
    Base class for structured content within a message.
    Each StructureContent represents a specific type of content in a message card.
    """
    content_type: ContentType
    title: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    content_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ContentStatus = ContentStatus.CREATING
    parent_id: Optional[str] = None  # For tracking hierarchical content (e.g., tool → tool_progress)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the StructureContent to a dictionary representation."""
        return {
            "content_id": self.content_id,
            "content_type": self.content_type.value,
            "title": self.title,
            "description": self.description,
            "data": self._get_data(),
            "metadata": self.metadata,
            "status": self.status.value,
            "parent_id": self.parent_id
        }

    def _get_data(self) -> Dict[str, Any]:
        """Get the data payload for this content. Override in subclasses."""
        return {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StructureContent':
        """Create a StructureContent from a dictionary."""
        content_type = ContentType(data["content_type"])
        # Dispatch to appropriate subclass
        subclass = _CONTENT_CLASS_MAP.get(content_type, cls)
        return subclass.from_dict(data)

    def update(self, **kwargs):
        """Update content fields and set status to UPDATING."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.status = ContentStatus.UPDATING

    def complete(self):
        """Mark content as completed."""
        self.status = ContentStatus.COMPLETED

    def fail(self, error: str = None):
        """Mark content as failed."""
        self.status = ContentStatus.FAILED
        if error:
            self.metadata["error"] = error


@dataclass
class TextContent(StructureContent):
    """Plain text content."""
    content_type: ContentType = ContentType.TEXT
    text: str = ""

    def _get_data(self) -> Dict[str, Any]:
        return {"text": self.text}


@dataclass
class ThinkingContent(StructureContent):
    """Agent thinking process content."""
    content_type: ContentType = ContentType.THINKING
    thought: str = ""
    step: Optional[int] = None
    total_steps: Optional[int] = None

    def _get_data(self) -> Dict[str, Any]:
        data = {"thought": self.thought}
        if self.step is not None:
            data["step"] = self.step
        if self.total_steps is not None:
            data["total_steps"] = self.total_steps
        return data


@dataclass
class ToolCallContent(StructureContent):
    """Tool call content with execution details."""
    content_type: ContentType = ContentType.TOOL_CALL
    tool_name: str = ""
    tool_input: Dict[str, Any] = field(default_factory=dict)
    tool_status: str = "started"  # Renamed to avoid conflict with StructureContent.status

    def _get_data(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "status": self.tool_status
        }


@dataclass
class ToolResponseContent(StructureContent):
    """Tool execution result content."""
    content_type: ContentType = ContentType.TOOL_RESPONSE
    tool_name: str = ""
    result: Optional[Any] = None
    error: Optional[str] = None
    tool_status: str = "completed"  # completed, failed

    def _get_data(self) -> Dict[str, Any]:
        data = {
            "tool_name": self.tool_name,
            "status": self.tool_status
        }
        if self.result is not None:
            data["result"] = self.result
        if self.error:
            data["error"] = self.error
        return data


@dataclass
class ProgressContent(StructureContent):
    """Progress update content."""
    content_type: ContentType = ContentType.PROGRESS
    progress: Union[str, int, float] = ""
    percentage: Optional[int] = None
    tool_name: Optional[str] = None

    def _get_data(self) -> Dict[str, Any]:
        data = {"progress": self.progress}
        if self.percentage is not None:
            data["percentage"] = self.percentage
        if self.tool_name:
            data["tool_name"] = self.tool_name
        return data


@dataclass
class CodeBlockContent(StructureContent):
    """Code block content with syntax highlighting."""
    content_type: ContentType = ContentType.CODE_BLOCK
    code: str = ""
    language: str = "python"
    filename: Optional[str] = None

    def _get_data(self) -> Dict[str, Any]:
        data = {
            "code": self.code,
            "language": self.language
        }
        if self.filename:
            data["filename"] = self.filename
        return data


@dataclass
class ImageContent(StructureContent):
    """Image content."""
    content_type: ContentType = ContentType.IMAGE
    url: Optional[str] = None
    alt_text: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

    def _get_data(self) -> Dict[str, Any]:
        data = {}
        if self.url:
            data["url"] = self.url
        if self.alt_text:
            data["alt_text"] = self.alt_text
        if self.width:
            data["width"] = self.width
        if self.height:
            data["height"] = self.height
        return data


@dataclass
class VideoContent(StructureContent):
    """Video content."""
    content_type: ContentType = ContentType.VIDEO
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None  # in seconds

    def _get_data(self) -> Dict[str, Any]:
        data = {}
        if self.url:
            data["url"] = self.url
        if self.thumbnail_url:
            data["thumbnail_url"] = self.thumbnail_url
        if self.duration:
            data["duration"] = self.duration
        return data


@dataclass
class MetadataContent(StructureContent):
    """Metadata content (e.g., todo updates, task status)."""
    content_type: ContentType = ContentType.METADATA
    metadata_type: str = ""  # e.g., "todo_update", "task_status"
    metadata_data: Dict[str, Any] = field(default_factory=dict)

    def _get_data(self) -> Dict[str, Any]:
        return {
            "metadata_type": self.metadata_type,
            "data": self.metadata_data
        }


@dataclass
class ErrorContent(StructureContent):
    """Error message content."""
    content_type: ContentType = ContentType.ERROR
    error_message: str = ""
    error_type: Optional[str] = None
    details: Optional[str] = None

    def _get_data(self) -> Dict[str, Any]:
        data = {"error": self.error_message}
        if self.error_type:
            data["error_type"] = self.error_type
        if self.details:
            data["details"] = self.details
        return data


@dataclass
class FileAttachmentContent(StructureContent):
    """File attachment content."""
    content_type: ContentType = ContentType.FILE_ATTACHMENT
    filename: str = ""
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None

    def _get_data(self) -> Dict[str, Any]:
        data = {"filename": self.filename}
        if self.file_path:
            data["file_path"] = self.file_path
        if self.file_size:
            data["file_size"] = self.file_size
        if self.mime_type:
            data["mime_type"] = self.mime_type
        return data


# Mapping of ContentType to appropriate subclass
_CONTENT_CLASS_MAP: Dict[ContentType, type] = {
    ContentType.TEXT: TextContent,
    ContentType.THINKING: ThinkingContent,
    ContentType.TOOL_CALL: ToolCallContent,
    ContentType.TOOL_RESPONSE: ToolResponseContent,
    ContentType.PROGRESS: ProgressContent,
    ContentType.CODE_BLOCK: CodeBlockContent,
    ContentType.IMAGE: ImageContent,
    ContentType.VIDEO: VideoContent,
    ContentType.METADATA: MetadataContent,
    ContentType.ERROR: ErrorContent,
    ContentType.FILE_ATTACHMENT: FileAttachmentContent,
}


def create_content(content_type: ContentType, **kwargs) -> StructureContent:
    """
    Factory function to create appropriate StructureContent subclass.

    Args:
        content_type: Type of content to create
        **kwargs: Arguments to pass to the content class constructor

    Returns:
        Appropriate StructureContent subclass instance
    """
    content_class = _CONTENT_CLASS_MAP.get(content_type, StructureContent)
    return content_class(content_type=content_type, **kwargs)
