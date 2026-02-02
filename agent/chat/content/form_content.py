"""Form content for Filmeto agent system."""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


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
