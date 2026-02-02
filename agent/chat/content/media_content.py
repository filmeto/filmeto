"""Media content for Filmeto agent system."""
from typing import Any, Dict, Optional
from dataclasses import dataclass

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


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
