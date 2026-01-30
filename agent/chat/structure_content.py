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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextContent':
        """Create a TextContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            text=data_dict.get("text", "")
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThinkingContent':
        """Create a ThinkingContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            thought=data_dict.get("thought", ""),
            step=data_dict.get("step"),
            total_steps=data_dict.get("total_steps")
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolCallContent':
        """Create a ToolCallContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            tool_name=data_dict.get("tool_name", ""),
            tool_input=data_dict.get("tool_input", {}),
            tool_status=data_dict.get("status", "started")
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolResponseContent':
        """Create a ToolResponseContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            tool_name=data_dict.get("tool_name", ""),
            result=data_dict.get("result"),
            error=data_dict.get("error"),
            tool_status=data_dict.get("status", "completed")
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressContent':
        """Create a ProgressContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            progress=data_dict.get("progress", ""),
            percentage=data_dict.get("percentage"),
            tool_name=data_dict.get("tool_name")
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeBlockContent':
        """Create a CodeBlockContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            code=data_dict.get("code", ""),
            language=data_dict.get("language", "python"),
            filename=data_dict.get("filename")
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImageContent':
        """Create a ImageContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            url=data_dict.get("url"),
            alt_text=data_dict.get("alt_text"),
            width=data_dict.get("width"),
            height=data_dict.get("height")
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoContent':
        """Create a VideoContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            url=data_dict.get("url"),
            thumbnail_url=data_dict.get("thumbnail_url"),
            duration=data_dict.get("duration")
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetadataContent':
        """Create a MetadataContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            metadata_type=data_dict.get("metadata_type", ""),
            metadata_data=data_dict.get("data", {})
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorContent':
        """Create a ErrorContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            error_message=data_dict.get("error", ""),
            error_type=data_dict.get("error_type"),
            details=data_dict.get("details")
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileAttachmentContent':
        """Create a FileAttachmentContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            filename=data_dict.get("filename", ""),
            file_path=data_dict.get("file_path"),
            file_size=data_dict.get("file_size"),
            mime_type=data_dict.get("mime_type")
        )


@dataclass
class AudioContent(StructureContent):
    """Audio content."""
    content_type: ContentType = ContentType.AUDIO
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None  # in seconds
    transcript: Optional[str] = None  # 转录文本

    def _get_data(self) -> Dict[str, Any]:
        data = {}
        if self.url:
            data["url"] = self.url
        if self.thumbnail_url:
            data["thumbnail_url"] = self.thumbnail_url
        if self.duration is not None:
            data["duration"] = self.duration
        if self.transcript:
            data["transcript"] = self.transcript
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioContent':
        """Create a AudioContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            url=data_dict.get("url"),
            thumbnail_url=data_dict.get("thumbnail_url"),
            duration=data_dict.get("duration"),
            transcript=data_dict.get("transcript")
        )


@dataclass
class TableContent(StructureContent):
    """Table content for displaying structured data."""
    content_type: ContentType = ContentType.TABLE
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    table_title: Optional[str] = None

    def _get_data(self) -> Dict[str, Any]:
        data = {
            "headers": self.headers,
            "rows": self.rows
        }
        if self.table_title:
            data["title"] = self.table_title
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TableContent':
        """Create a TableContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            headers=data_dict.get("headers", []),
            rows=data_dict.get("rows", []),
            table_title=data_dict.get("title")
        )


@dataclass
class ChartContent(StructureContent):
    """Chart content for visualizing data."""
    content_type: ContentType = ContentType.CHART
    chart_type: str = ""  # bar, line, pie, scatter, etc.
    data: Dict[str, Any] = field(default_factory=dict)
    chart_title: Optional[str] = None
    x_axis_label: Optional[str] = None
    y_axis_label: Optional[str] = None

    def _get_data(self) -> Dict[str, Any]:
        data = {
            "chart_type": self.chart_type,
            "data": self.data
        }
        if self.chart_title:
            data["title"] = self.chart_title
        if self.x_axis_label:
            data["x_axis_label"] = self.x_axis_label
        if self.y_axis_label:
            data["y_axis_label"] = self.y_axis_label
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChartContent':
        """Create a ChartContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            chart_type=data_dict.get("chart_type", ""),
            data=data_dict.get("data", {}),
            chart_title=data_dict.get("title"),
            x_axis_label=data_dict.get("x_axis_label"),
            y_axis_label=data_dict.get("y_axis_label")
        )


@dataclass
class LinkContent(StructureContent):
    """Link content for URLs."""
    content_type: ContentType = ContentType.LINK
    url: str = ""
    link_title: Optional[str] = None
    description: Optional[str] = None
    favicon_url: Optional[str] = None

    def _get_data(self) -> Dict[str, Any]:
        data = {"url": self.url}
        if self.link_title:
            data["title"] = self.link_title
        if self.description:
            data["description"] = self.description
        if self.favicon_url:
            data["favicon_url"] = self.favicon_url
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LinkContent':
        """Create a LinkContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            url=data_dict.get("url", ""),
            link_title=data_dict.get("title"),
            description=data_dict.get("description"),
            favicon_url=data_dict.get("favicon_url")
        )


@dataclass
class ButtonContent(StructureContent):
    """Button content for interactive elements."""
    content_type: ContentType = ContentType.BUTTON
    label: str = ""
    action: str = ""  # Action to perform when clicked
    button_style: str = "primary"  # primary, secondary, danger, warning, success
    disabled: bool = False
    payload: Optional[Dict[str, Any]] = None  # Additional data for the action

    def _get_data(self) -> Dict[str, Any]:
        data = {
            "label": self.label,
            "action": self.action,
            "style": self.button_style,
            "disabled": self.disabled
        }
        if self.payload:
            data["payload"] = self.payload
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ButtonContent':
        """Create a ButtonContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            label=data_dict.get("label", ""),
            action=data_dict.get("action", ""),
            button_style=data_dict.get("style", "primary"),
            disabled=data_dict.get("disabled", False),
            payload=data_dict.get("payload")
        )


@dataclass
class FormContent(StructureContent):
    """Form content for interactive input."""
    content_type: ContentType = ContentType.FORM
    fields: List[Dict[str, Any]] = field(default_factory=list)
    submit_action: str = ""
    submit_label: str = "Submit"
    form_title: Optional[str] = None

    def _get_data(self) -> Dict[str, Any]:
        data = {
            "fields": self.fields,
            "submit_action": self.submit_action,
            "submit_label": self.submit_label
        }
        if self.form_title:
            data["title"] = self.form_title
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FormContent':
        """Create a FormContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            fields=data_dict.get("fields", []),
            submit_action=data_dict.get("submit_action", ""),
            submit_label=data_dict.get("submit_label", "Submit"),
            form_title=data_dict.get("title")
        )


@dataclass
class SkillContent(StructureContent):
    """Skill information content."""
    content_type: ContentType = ContentType.SKILL
    skill_name: str = ""
    skill_description: str = ""
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    example_call: Optional[str] = None
    usage_criteria: Optional[str] = None

    def _get_data(self) -> Dict[str, Any]:
        data = {
            "skill_name": self.skill_name,
            "description": self.skill_description,
            "parameters": self.parameters
        }
        if self.example_call:
            data["example_call"] = self.example_call
        if self.usage_criteria:
            data["usage_criteria"] = self.usage_criteria
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillContent':
        """Create a SkillContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            skill_name=data_dict.get("skill_name", ""),
            skill_description=data_dict.get("description", ""),
            parameters=data_dict.get("parameters", []),
            example_call=data_dict.get("example_call"),
            usage_criteria=data_dict.get("usage_criteria")
        )


@dataclass
class PlanContent(StructureContent):
    """Plan content for task planning."""
    content_type: ContentType = ContentType.PLAN
    plan_id: str = ""
    plan_title: Optional[str] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    total_steps: int = 0
    plan_status: str = "pending"  # pending, in_progress, completed, failed

    def _get_data(self) -> Dict[str, Any]:
        data = {
            "plan_id": self.plan_id,
            "steps": self.steps,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "status": self.plan_status
        }
        if self.plan_title:
            data["title"] = self.plan_title
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlanContent':
        """Create a PlanContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            plan_id=data_dict.get("plan_id", ""),
            plan_title=data_dict.get("title"),
            steps=data_dict.get("steps", []),
            current_step=data_dict.get("current_step", 0),
            total_steps=data_dict.get("total_steps", 0),
            plan_status=data_dict.get("status", "pending")
        )


@dataclass
class StepContent(StructureContent):
    """Step content within a plan."""
    content_type: ContentType = ContentType.STEP
    step_id: str = ""
    step_number: int = 0
    description: str = ""
    step_status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None
    estimated_duration: Optional[int] = None  # in seconds

    def _get_data(self) -> Dict[str, Any]:
        data = {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "description": self.description,
            "status": self.step_status
        }
        if self.result is not None:
            data["result"] = self.result
        if self.error:
            data["error"] = self.error
        if self.estimated_duration is not None:
            data["estimated_duration"] = self.estimated_duration
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StepContent':
        """Create a StepContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            step_id=data_dict.get("step_id", ""),
            step_number=data_dict.get("step_number", 0),
            description=data_dict.get("description", ""),
            step_status=data_dict.get("status", "pending"),
            result=data_dict.get("result"),
            error=data_dict.get("error"),
            estimated_duration=data_dict.get("estimated_duration")
        )


@dataclass
class TaskListContent(StructureContent):
    """Task list content for tracking multiple tasks."""
    content_type: ContentType = ContentType.TASK_LIST
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    completed_count: int = 0
    total_count: int = 0
    list_title: Optional[str] = None

    def _get_data(self) -> Dict[str, Any]:
        data = {
            "tasks": self.tasks,
            "completed_count": self.completed_count,
            "total_count": self.total_count
        }
        if self.list_title:
            data["title"] = self.list_title
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskListContent':
        """Create a TaskListContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            tasks=data_dict.get("tasks", []),
            completed_count=data_dict.get("completed_count", 0),
            total_count=data_dict.get("total_count", 0),
            list_title=data_dict.get("title")
        )


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
    ContentType.AUDIO: AudioContent,
    ContentType.TABLE: TableContent,
    ContentType.CHART: ChartContent,
    ContentType.LINK: LinkContent,
    ContentType.BUTTON: ButtonContent,
    ContentType.FORM: FormContent,
    ContentType.METADATA: MetadataContent,
    ContentType.ERROR: ErrorContent,
    ContentType.FILE_ATTACHMENT: FileAttachmentContent,
    ContentType.SKILL: SkillContent,
    ContentType.PLAN: PlanContent,
    ContentType.STEP: StepContent,
    ContentType.TASK_LIST: TaskListContent,
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
