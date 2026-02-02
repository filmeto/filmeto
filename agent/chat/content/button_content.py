"""Button content for Filmeto agent system."""
from typing import Any, Dict, Optional
from dataclasses import dataclass

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


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
