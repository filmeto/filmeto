"""MessageConverter – pure-Python ChatListItem → QML dict conversion.

Extracted from AgentChatListModel so that background threads can call
the conversion without touching any Qt object.  All role-name constants are
duplicated here as class attributes so this module has zero dependency on
PySide6 at import time.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_types import ContentType
from agent.chat.content import StructureContent
from agent.react.json_utils import JsonExtractor
from app.ui.chat.list.agent_chat_list_items import ChatListItem

logger = logging.getLogger(__name__)


class MessageConverter:
    """Stateless converter: ChatListItem / AgentMessage → QML-compatible dict.

    All methods are static so the class can be used without instantiation.
    Constants mirror AgentChatListModel role names exactly; if you rename a
    role there, rename it here too.
    """

    # ── Role name constants (kept in sync with AgentChatListModel) ─────────
    MESSAGE_ID = "messageId"
    SENDER_ID = "senderId"
    SENDER_NAME = "senderName"
    IS_USER = "isUser"
    CONTENT = "content"
    AGENT_COLOR = "agentColor"
    AGENT_ICON = "agentIcon"
    CREW_METADATA = "crewMetadata"
    STRUCTURED_CONTENT = "structuredContent"
    CONTENT_TYPE = "contentType"
    IS_READ = "isRead"
    TIMESTAMP = "timestamp"
    DATE_GROUP = "dateGroup"
    START_TIME = "startTime"
    DURATION = "duration"
    CREW_READ_BY = "crewReadBy"

    # ── Public API ───────────────────────────────────────────────────────────

    @staticmethod
    def from_chat_list_item(chat_list_item: ChatListItem) -> Dict[str, Any]:
        """Convert a ChatListItem to a QML model dict.

        Thread-safe: no Qt objects are accessed.
        """
        from agent.chat.content import TextContent, ThinkingContent
        from app.ui.chat.list.agent_chat_list_model import (
            _format_start_time, _get_date_group, _format_duration,
        )

        if not isinstance(chat_list_item, ChatListItem):
            return {}

        # ── timestamp ───────────────────────────────────────────────────────
        timestamp = None
        if chat_list_item.is_user:
            timestamp = chat_list_item.metadata.get('timestamp')
        elif chat_list_item.agent_message and chat_list_item.agent_message.metadata:
            timestamp = chat_list_item.agent_message.metadata.get('timestamp')
            if not timestamp:
                timestamp = chat_list_item.metadata.get('timestamp')

        # ── plain-text preview (content field) ──────────────────────────────
        content = ""
        if chat_list_item.is_user:
            content = chat_list_item.user_content
        elif chat_list_item.agent_message:
            content = MessageConverter._extract_content(
                chat_list_item.agent_message.structured_content
            )

        # ── primary content type ─────────────────────────────────────────────
        content_type = "text"
        if not chat_list_item.is_user and chat_list_item.agent_message:
            content_type = MessageConverter._primary_content_type(
                chat_list_item.agent_message.structured_content, content
            )

        # ── structured content ───────────────────────────────────────────────
        structured_content: List[Dict[str, Any]] = []
        if not chat_list_item.is_user and chat_list_item.agent_message:
            structured_content = MessageConverter._serialize_structured_content(
                chat_list_item.agent_message.structured_content
            )

        # ── time formatting ──────────────────────────────────────────────────
        start_time = _format_start_time(timestamp)
        duration = MessageConverter._calc_duration(
            chat_list_item, timestamp
        )

        result = {
            MessageConverter.MESSAGE_ID: chat_list_item.message_id,
            MessageConverter.SENDER_ID: chat_list_item.sender_id,
            MessageConverter.SENDER_NAME: chat_list_item.sender_name,
            MessageConverter.IS_USER: chat_list_item.is_user,
            MessageConverter.CONTENT: content,
            MessageConverter.AGENT_COLOR: chat_list_item.agent_color,
            MessageConverter.AGENT_ICON: chat_list_item.agent_icon,
            MessageConverter.CREW_METADATA: chat_list_item.crew_member_metadata,
            MessageConverter.STRUCTURED_CONTENT: structured_content,
            MessageConverter.CONTENT_TYPE: content_type,
            MessageConverter.IS_READ: True,
            MessageConverter.TIMESTAMP: timestamp,
            MessageConverter.DATE_GROUP: _get_date_group(timestamp),
            MessageConverter.START_TIME: start_time,
            MessageConverter.DURATION: duration,
            MessageConverter.CREW_READ_BY: getattr(chat_list_item, "crew_read_by", None) or [],
        }
        return result

    @staticmethod
    def from_agent_message(
        agent_message: AgentMessage,
        agent_color: str = "#4a90e2",
        agent_icon: str = "🤖",
        crew_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convert an AgentMessage to a QML model dict.

        Thread-safe: no Qt objects are accessed.
        """
        from app.ui.chat.list.agent_chat_list_model import (
            _format_start_time, _get_date_group, _format_duration,
        )

        timestamp = None
        if agent_message.metadata:
            timestamp = agent_message.metadata.get('timestamp')

        content_type = "text"
        for sc in agent_message.structured_content:
            if sc.content_type != ContentType.TEXT:
                content_type = sc.content_type.value
                break

        structured_content = MessageConverter._serialize_structured_content(
            agent_message.structured_content
        )

        start_time = _format_start_time(timestamp)
        has_typing = any(
            getattr(sc, 'content_type', None) == ContentType.TYPING
            for sc in agent_message.structured_content
        )
        end_timestamp = agent_message.metadata.get('end_timestamp') if agent_message.metadata else None
        duration = _format_duration(timestamp, end_timestamp) if (not has_typing or end_timestamp) else ""

        return {
            MessageConverter.MESSAGE_ID: agent_message.message_id,
            MessageConverter.SENDER_ID: agent_message.sender_id,
            MessageConverter.SENDER_NAME: agent_message.sender_name,
            MessageConverter.IS_USER: False,
            MessageConverter.CONTENT: "",
            MessageConverter.AGENT_COLOR: agent_color,
            MessageConverter.AGENT_ICON: agent_icon,
            MessageConverter.CREW_METADATA: crew_metadata or {},
            MessageConverter.STRUCTURED_CONTENT: structured_content,
            MessageConverter.CONTENT_TYPE: content_type,
            MessageConverter.IS_READ: True,
            MessageConverter.TIMESTAMP: timestamp,
            MessageConverter.DATE_GROUP: _get_date_group(timestamp),
            MessageConverter.START_TIME: start_time,
            MessageConverter.DURATION: duration,
            MessageConverter.CREW_READ_BY: [],
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _serialize_structured_content(
        structured_content: List[StructureContent],
    ) -> List[Dict[str, Any]]:
        """Convert StructureContent objects to plain dicts for QML."""
        result = []
        for sc in structured_content:
            if hasattr(sc, 'to_dict'):
                result.append(sc.to_dict())
            else:
                result.append({
                    'content_type': getattr(sc, 'content_type', 'text'),
                    'data': getattr(sc, 'data', {}),
                })
        return result

    @staticmethod
    def _extract_content(structured_content: List[StructureContent]) -> str:
        """Extract a plain-text preview from structured content."""
        from agent.chat.content import TextContent, ThinkingContent

        # First pass: look for primary content types
        for sc in structured_content:
            sc_type = getattr(sc, 'content_type', ContentType.TEXT)
            if sc_type == ContentType.TEXT and isinstance(sc, TextContent):
                return sc.text or ""
            if sc_type == ContentType.THINKING:
                if isinstance(sc, ThinkingContent):
                    return sc.thought or ""
                if hasattr(sc, 'data') and isinstance(sc.data, dict):
                    return sc.data.get('thought', '')
                return ""
            if sc_type == ContentType.PROGRESS:
                if hasattr(sc, 'data') and isinstance(sc.data, dict):
                    return sc.data.get('progress', '')
                return ""
            if sc_type == ContentType.TOOL_CALL:
                if hasattr(sc, 'data') and isinstance(sc.data, dict):
                    tool_name = sc.data.get('tool_name', '')
                    return f"调用工具: {tool_name}" if tool_name else ""
                return ""
            if sc_type == ContentType.TYPING:
                continue

        # Second pass: fallback to any extractable text
        for sc in structured_content:
            if hasattr(sc, 'text') and sc.text:
                return sc.text
            if hasattr(sc, 'data') and isinstance(sc.data, dict):
                data = sc.data
                if 'text' in data:
                    return MessageConverter._unwrap_json_text(data['text'])
                if 'progress' in data:
                    return data['progress']
                if 'thought' in data:
                    return data['thought']
                if 'tool_name' in data:
                    return f"工具: {data['tool_name']}"

        # Last resort: placeholder for typing/metadata-only messages
        if structured_content:
            first_type = getattr(structured_content[0], 'content_type', None)
            if first_type in {ContentType.METADATA, ContentType.TYPING, ContentType.PROGRESS}:
                has_real = any(
                    getattr(sc, 'content_type', None) != ContentType.TYPING
                    for sc in structured_content
                )
                if not has_real:
                    return "..."
        return ""

    @staticmethod
    def _unwrap_json_text(text_value: str) -> str:
        """Try to unwrap a JSON-in-markdown-code-block response.

        Uses JsonExtractor for consistent handling of code block formats.
        """
        if not text_value or not isinstance(text_value, str):
            return text_value or ""

        # Use JsonExtractor to get raw code block content
        content = JsonExtractor.extract_code_block_content(text_value)
        if not content:
            return text_value

        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and 'final' in parsed:
                return parsed['final']
            if isinstance(parsed, str):
                return parsed
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.debug(f"Failed to parse JSON code block: {e}")

        return text_value

    @staticmethod
    def _primary_content_type(
        structured_content: List[StructureContent],
        content: str,
    ) -> str:
        """Determine the primary content type string for QML delegate selection."""
        type_priority = {
            ContentType.TEXT, ContentType.THINKING,
            ContentType.PROGRESS, ContentType.TOOL_CALL,
        }
        for sc in structured_content:
            ct = getattr(sc, 'content_type', None)
            if ct in type_priority:
                return ct.value

        if not content:
            for sc in structured_content:
                if getattr(sc, 'content_type', None) == ContentType.TYPING:
                    return "typing"
        return "text"

    @staticmethod
    def _calc_duration(item: ChatListItem, timestamp: Any) -> str:
        """Calculate the formatted duration for a ChatListItem."""
        from app.ui.chat.list.agent_chat_list_model import _format_duration

        if item.is_user:
            end_ts = item.metadata.get('end_timestamp')
            return _format_duration(timestamp, end_ts) if end_ts else ""

        if item.agent_message:
            has_typing = any(
                getattr(sc, 'content_type', None) == ContentType.TYPING
                for sc in item.agent_message.structured_content
            )
            end_ts = None
            if item.agent_message.metadata:
                end_ts = item.agent_message.metadata.get('end_timestamp')
            if not has_typing or end_ts:
                return _format_duration(timestamp, end_ts)
        return ""
