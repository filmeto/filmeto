"""Tool content for Filmeto agent system."""
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


@dataclass
class ToolCallContent(StructureContent):
    """Tool call content with execution details."""
    content_type: ContentType = ContentType.TOOL_CALL
    tool_name: str = ""
    tool_input: Dict[str, Any] = field(default_factory=dict)
    tool_status: str = "started"  # started, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None
    # Unique identifier for tracking tool lifecycle (used for merging events)
    tool_call_id: str = ""

    def set_result(self, result: Any, error: Optional[str] = None) -> None:
        """Set the result of the tool execution.

        Args:
            result: The result value from tool execution
            error: Optional error message if execution failed
        """
        self.result = result
        if error:
            self.error = error
            self.tool_status = "failed"
        else:
            self.tool_status = "completed"

    def _get_data(self) -> Dict[str, Any]:
        data = {
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "status": self.tool_status
        }
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        if self.result is not None:
            data["result"] = self.result
        if self.error:
            data["error"] = self.error
        return data

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
            tool_status=data_dict.get("status", "started"),
            result=data_dict.get("result"),
            error=data_dict.get("error"),
            tool_call_id=data_dict.get("tool_call_id", "")
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
