"""Link content for Filmeto agent system."""
from typing import Any, Dict, Optional
from dataclasses import dataclass

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


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
