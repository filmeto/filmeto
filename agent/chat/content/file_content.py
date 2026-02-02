"""File content for Filmeto agent system."""
from typing import Any, Dict, Optional
from dataclasses import dataclass

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


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
