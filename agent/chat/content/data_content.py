"""Data content (table, chart) for Filmeto agent system."""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


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
