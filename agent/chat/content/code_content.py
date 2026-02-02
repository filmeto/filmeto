"""Code content for Filmeto agent system."""
from typing import Any, Dict, Optional
from dataclasses import dataclass

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


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
