"""QML-compatible model for agent chat list.

This module provides a QAbstractListModel that exposes chat data to QML,
with proper role names and automatic date grouping for separators.

Performance optimizations:
- Batched dataChanged emission: Multiple rapid update_item calls within
  a single frame (~16ms) are batched into a single dataChanged signal,
  reducing redundant QML binding re-evaluations during streaming.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, QObject, Slot, Property, QTimer, Signal

from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_types import ContentType
from agent.chat.content import StructureContent

logger = logging.getLogger(__name__)


class QmlAgentChatListModel(QAbstractListModel):
    """QML-compatible model for chat messages.

    This model exposes chat message data to QML with proper role names
    and automatic date grouping for message separators.

    Performance: update_item() batches dataChanged signals using a 16ms timer
    (~1 frame at 60fps). Multiple updates within a frame result in a single
    dataChanged emission covering the entire dirty range.

    Roles exposed to QML:
    - messageId: Unique message identifier
    - senderId: Sender's identifier
    - senderName: Display name of sender
    - isUser: Whether message is from user
    - content: Plain text content
    - agentColor: Color for agent avatar
    - agentIcon: Icon for agent avatar
    - crewMetadata: Additional crew member metadata
    - structuredContent: List of structured content items
    - contentType: Primary content type for delegate selection
    - isRead: Read status for user messages
    - timestamp: Message timestamp for date grouping
    - dateGroup: Date group key for section headers
    """

    # Batched dataChanged interval (~1 frame at 60fps)
    BATCH_UPDATE_INTERVAL_MS = 16

    # Role names for QML
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
    START_TIME = "startTime"  # Formatted start time (HH:MM)
    DURATION = "duration"     # Formatted duration (e.g., "2m 30s")

    # Signal emitted after a batch of updates is flushed to QML
    batchFlushed = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._items: List[Dict[str, Any]] = []
        self._message_id_to_row: Dict[str, int] = {}

        # Batched dataChanged support
        self._dirty_rows: Set[int] = set()
        self._batch_timer = QTimer(self)
        self._batch_timer.setInterval(self.BATCH_UPDATE_INTERVAL_MS)
        self._batch_timer.setSingleShot(True)
        self._batch_timer.timeout.connect(self._flush_dirty_rows)

    def roleNames(self):
        """Return role names for QML binding."""
        from PySide6.QtCore import QByteArray
        return {
            Qt.UserRole + 1: QByteArray(self.MESSAGE_ID.encode()),
            Qt.UserRole + 2: QByteArray(self.SENDER_ID.encode()),
            Qt.UserRole + 3: QByteArray(self.SENDER_NAME.encode()),
            Qt.UserRole + 4: QByteArray(self.IS_USER.encode()),
            Qt.UserRole + 5: QByteArray(self.CONTENT.encode()),
            Qt.UserRole + 6: QByteArray(self.AGENT_COLOR.encode()),
            Qt.UserRole + 7: QByteArray(self.AGENT_ICON.encode()),
            Qt.UserRole + 8: QByteArray(self.CREW_METADATA.encode()),
            Qt.UserRole + 9: QByteArray(self.STRUCTURED_CONTENT.encode()),
            Qt.UserRole + 10: QByteArray(self.CONTENT_TYPE.encode()),
            Qt.UserRole + 11: QByteArray(self.IS_READ.encode()),
            Qt.UserRole + 12: QByteArray(self.TIMESTAMP.encode()),
            Qt.UserRole + 13: QByteArray(self.DATE_GROUP.encode()),
            Qt.UserRole + 14: QByteArray(self.START_TIME.encode()),
            Qt.UserRole + 15: QByteArray(self.DURATION.encode()),
        }

    def rowCount(self, parent: QModelIndex = None) -> int:
        """Return number of rows in the model."""
        if parent is None:
            parent = QModelIndex()
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Return data for the given index and role."""
        if not index.isValid():
            return None

        row = index.row()
        if row >= len(self._items):
            return None

        item = self._items[row]

        # Use roleNames to get the role name (QByteArray)
        role_names = self.roleNames()
        role_name_bytes = role_names.get(role)

        if role_name_bytes:
            # Convert QByteArray to string for dict lookup
            role_name = role_name_bytes.data().decode()
            return item.get(role_name)

        return None

    def add_item(self, item: Dict[str, Any]) -> int:
        """Add a single item to the end of the model.

        Args:
            item: Dictionary containing message data

        Returns:
            Row index where the item was added
        """
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(item)
        if item.get(self.MESSAGE_ID):
            self._message_id_to_row[item[self.MESSAGE_ID]] = row
        self.endInsertRows()
        return row

    def prepend_items(self, items: List[Dict[str, Any]]) -> int:
        """Insert items at the beginning of the model.

        Args:
            items: List of message dictionaries to prepend

        Returns:
            Number of items prepended
        """
        if not items:
            return 0
        count = len(items)
        self.beginInsertRows(QModelIndex(), 0, count - 1)
        self._items = list(items) + self._items
        # Rebuild index map
        self._message_id_to_row.clear()
        for i, item in enumerate(self._items):
            msg_id = item.get(self.MESSAGE_ID)
            if msg_id:
                self._message_id_to_row[msg_id] = i
        self.endInsertRows()
        return count

    def remove_first_n(self, n: int) -> None:
        """Remove first n items from the model."""
        total = len(self._items)
        if n <= 0 or n > total:
            return
        self.beginRemoveRows(QModelIndex(), 0, n - 1)
        for i in range(n):
            item = self._items[i]
            msg_id = item.get(self.MESSAGE_ID)
            if msg_id:
                self._message_id_to_row.pop(msg_id, None)
        self._items = self._items[n:]
        self.endRemoveRows()

    def remove_last_n(self, n: int) -> None:
        """Remove last n items from the model."""
        total = len(self._items)
        if n <= 0 or n > total:
            return
        start = total - n
        self.beginRemoveRows(QModelIndex(), start, total - 1)
        for i in range(start, total):
            item = self._items[i]
            msg_id = item.get(self.MESSAGE_ID)
            if msg_id:
                self._message_id_to_row.pop(msg_id, None)
        self._items = self._items[:start]
        self.endRemoveRows()

    def update_item(self, message_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing item with batched dataChanged emission.

        The internal data is updated immediately, but the dataChanged signal
        is deferred and batched with other updates within ~16ms. This prevents
        redundant QML binding re-evaluations during rapid streaming updates.

        Args:
            message_id: ID of message to update
            updates: Dictionary of fields to update

        Returns:
            True if item was found and updated
        """
        row = self._message_id_to_row.get(message_id)
        if row is None:
            return False

        if row >= len(self._items):
            return False

        self._items[row].update(updates)

        # Mark row as dirty and schedule batched emission
        self._dirty_rows.add(row)
        if not self._batch_timer.isActive():
            self._batch_timer.start()

        return True

    def flush_updates(self) -> None:
        """Force immediate emission of any pending batched dataChanged signals.

        Call this before operations that depend on QML having received the latest
        data (e.g., scroll-to-bottom after content update).
        """
        if self._dirty_rows:
            self._batch_timer.stop()
            self._flush_dirty_rows()

    def _flush_dirty_rows(self) -> None:
        """Emit a single dataChanged signal covering all dirty rows."""
        if not self._dirty_rows:
            return

        min_row = min(self._dirty_rows)
        max_row = max(self._dirty_rows)
        self._dirty_rows.clear()

        top_left = self.index(min_row, 0)
        bottom_right = self.index(max_row, 0)
        self.dataChanged.emit(top_left, bottom_right)
        self.batchFlushed.emit()

    def get_item(self, row: int) -> Optional[Dict[str, Any]]:
        """Get item at the specified row."""
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def get_item_by_message_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get item by its message ID."""
        row = self._message_id_to_row.get(message_id)
        if row is not None and 0 <= row < len(self._items):
            return self._items[row]
        return None

    def get_row_by_message_id(self, message_id: str) -> Optional[int]:
        """Get row index for a message ID."""
        return self._message_id_to_row.get(message_id)

    def clear(self) -> None:
        """Clear all items from the model."""
        # Stop any pending batch updates
        self._batch_timer.stop()
        self._dirty_rows.clear()

        self.beginResetModel()
        self._items = []
        self._message_id_to_row = {}
        self.endResetModel()

    @staticmethod
    def _get_date_group(timestamp: Optional[float]) -> str:
        """Get date group key for message separators.

        Groups messages by:
        - Today
        - Yesterday
        - This week
        - Last week
        - This month
        - Older

        Args:
            timestamp: Unix timestamp (float) or ISO 8601 string (str)

        Returns:
            Date group string
        """
        if not timestamp:
            return ""

        # Handle both Unix timestamp (float) and ISO 8601 string
        if isinstance(timestamp, str):
            try:
                msg_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                # Try parsing as Unix timestamp
                try:
                    msg_date = datetime.fromtimestamp(float(timestamp))
                except (ValueError, TypeError):
                    logger.debug(f"Could not parse timestamp: {timestamp}")
                    return ""
        elif isinstance(timestamp, (int, float)):
            msg_date = datetime.fromtimestamp(timestamp)
        else:
            return ""

        now = datetime.now()
        today = now.date()
        yesterday = today - timedelta(days=1)
        this_week_start = today - timedelta(days=today.weekday())
        last_week_start = this_week_start - timedelta(days=7)
        this_month_start = now.replace(day=1)

        msg_date_only = msg_date.date()

        if msg_date_only == today:
            return "Today"
        elif msg_date_only == yesterday:
            return "Yesterday"
        elif msg_date_only >= this_week_start:
            return "This Week"
        elif msg_date_only >= last_week_start:
            return "Last Week"
        elif msg_date_only >= this_month_start.date():
            return "This Month"
        else:
            return msg_date.strftime("%B %Y")

    @staticmethod
    def _format_start_time(timestamp) -> str:
        """Format timestamp as start time with date context.

        Display format depends on how recent the message is:
        - Today: "HH:MM"
        - Yesterday: "昨天 HH:MM"
        - This year: "MM-DD HH:MM"
        - Older: "YYYY-MM-DD HH:MM"

        Args:
            timestamp: Unix timestamp (float) or ISO 8601 string

        Returns:
            Formatted time string
        """
        if not timestamp:
            return ""

        try:
            if isinstance(timestamp, str):
                msg_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif isinstance(timestamp, (int, float)):
                msg_date = datetime.fromtimestamp(timestamp)
            else:
                return ""

            now = datetime.now()
            today = now.date()
            msg_date_only = msg_date.date()

            if msg_date_only == today:
                # Today: just show time
                return msg_date.strftime("%H:%M")
            elif msg_date_only == today - timedelta(days=1):
                # Yesterday
                return f"昨天 {msg_date.strftime('%H:%M')}"
            elif msg_date.year == now.year:
                # This year: show month-day time
                return msg_date.strftime("%m-%d %H:%M")
            else:
                # Older: show full date
                return msg_date.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            return ""

    @staticmethod
    def _format_duration(start_timestamp, end_timestamp=None) -> str:
        """Format duration between start and end timestamps.

        Args:
            start_timestamp: Start time (Unix timestamp or ISO string)
            end_timestamp: End time (defaults to now if None)

        Returns:
            Formatted duration string (e.g., "45s", "2m 30s", "1h 15m")
        """
        if not start_timestamp:
            return ""

        try:
            if isinstance(start_timestamp, str):
                start_time = datetime.fromisoformat(start_timestamp.replace('Z', '+00:00'))
            elif isinstance(start_timestamp, (int, float)):
                start_time = datetime.fromtimestamp(start_timestamp)
            else:
                return ""

            if end_timestamp:
                if isinstance(end_timestamp, str):
                    end_time = datetime.fromisoformat(end_timestamp.replace('Z', '+00:00'))
                elif isinstance(end_timestamp, (int, float)):
                    end_time = datetime.fromtimestamp(end_timestamp)
                else:
                    end_time = datetime.now()
            else:
                end_time = datetime.now()

            delta = end_time - start_time
            total_seconds = int(delta.total_seconds())

            if total_seconds < 0:
                return ""

            if total_seconds < 60:
                return f"{total_seconds}s"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                if seconds > 0:
                    return f"{minutes}m {seconds}s"
                return f"{minutes}m"
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                if minutes > 0:
                    return f"{hours}h {minutes}m"
                return f"{hours}h"

        except (ValueError, TypeError):
            return ""

    @staticmethod
    def _serialize_structured_content(structured_content: List[StructureContent]) -> List[Dict[str, Any]]:
        """Convert structured content to QML-compatible format."""
        result = []
        for sc in structured_content:
            if hasattr(sc, 'to_dict'):
                result.append(sc.to_dict())
            else:
                # Fallback for older content types
                result.append({
                    'content_type': getattr(sc, 'content_type', 'text'),
                    'data': getattr(sc, 'data', {})
                })
        return result

    @classmethod
    def from_chat_list_item(cls, chat_list_item: 'ChatListItem') -> Dict[str, Any]:
        """Convert a ChatListItem to QML model item.

        Args:
            chat_list_item: ChatListItem instance

        Returns:
            Dictionary suitable for QML model
        """
        from app.ui.chat.list.agent_chat_list_items import ChatListItem
        from agent.chat.content import TextContent, ThinkingContent, TypingContent, ToolCallContent
        from agent.chat.content import ContentType
        from utils.i18n_utils import tr

        if not isinstance(chat_list_item, ChatListItem):
            return {}

        # Get timestamp from metadata
        # For user messages: use chat_list_item.metadata
        # For agent messages: use agent_message.metadata (with fallback to chat_list_item.metadata)
        timestamp = None
        if chat_list_item.is_user:
            # User message: get timestamp from item metadata
            timestamp = chat_list_item.metadata.get('timestamp')
        elif chat_list_item.agent_message and chat_list_item.agent_message.metadata:
            # Agent message: prefer agent_message metadata
            timestamp = chat_list_item.agent_message.metadata.get('timestamp')
            if not timestamp:
                timestamp = chat_list_item.metadata.get('timestamp')

        # Extract text content for quick access
        content = ""
        if chat_list_item.is_user:
            content = chat_list_item.user_content
        elif chat_list_item.agent_message:
            # Extract content based on content type
            for sc in chat_list_item.agent_message.structured_content:
                sc_type = sc.content_type if hasattr(sc, 'content_type') else ContentType.TEXT

                if sc_type == ContentType.TEXT and isinstance(sc, TextContent):
                    content = sc.text or ""
                    break
                elif sc_type == ContentType.THINKING:
                    if isinstance(sc, ThinkingContent):
                        content = sc.thought or ""
                    elif hasattr(sc, 'data') and isinstance(sc.data, dict):
                        content = sc.data.get('thought', '')
                    break
                elif sc_type == ContentType.PROGRESS:
                    if hasattr(sc, 'data') and isinstance(sc.data, dict):
                        content = sc.data.get('progress', '')
                    break
                elif sc_type == ContentType.TOOL_CALL:
                    if hasattr(sc, 'data') and isinstance(sc.data, dict):
                        tool_name = sc.data.get('tool_name', '')
                        if tool_name:
                            content = f"调用工具: {tool_name}"
                    break
                elif sc_type == ContentType.TYPING:
                    # Skip typing indicators for content display
                    continue

            # If still no content, try to get from any content item
            if not content:
                for sc in chat_list_item.agent_message.structured_content:
                    if hasattr(sc, 'text') and sc.text:
                        content = sc.text
                        break
                    elif hasattr(sc, 'data') and isinstance(sc.data, dict):
                        data = sc.data
                        if 'text' in data:
                            text_value = data['text']
                            # Check if text contains a JSON code block that needs parsing
                            if text_value and isinstance(text_value, str):
                                # Try to extract JSON from markdown code blocks
                                import re
                                # Match ```json\n{...}\n``` or ```\n{...}\n```
                                json_match = re.search(r'```(?:json)?\s*\n([\s\S]*?)\n```', text_value)
                                if json_match:
                                    try:
                                        inner_json = json_match.group(1).strip()
                                        parsed = json.loads(inner_json)
                                        # Extract 'final' field if it's a response wrapper
                                        if isinstance(parsed, dict) and 'final' in parsed:
                                            content = parsed['final']
                                        elif isinstance(parsed, str):
                                            content = parsed
                                        else:
                                            content = text_value
                                    except (json.JSONDecodeError, TypeError, ValueError) as e:
                                        logger.debug(f"Failed to parse JSON code block: {e}, using original text")
                                        # If parsing fails, use original text
                                        content = text_value
                                else:
                                    content = text_value
                            else:
                                content = text_value
                            break
                        elif 'progress' in data:
                            content = data['progress']
                            break
                        elif 'thought' in data:
                            content = data['thought']
                            break
                        elif 'tool_name' in data:
                            content = f"工具: {data['tool_name']}"
                            break

            # Use "..." for command/typing messages with no extractable content
            if not content and chat_list_item.agent_message:
                # Check if message is system/typing/metadata type without real content
                # Derive from first structured content item
                message_type = None
                if chat_list_item.agent_message.structured_content:
                    message_type = chat_list_item.agent_message.structured_content[0].content_type

                if message_type in {ContentType.METADATA, ContentType.TYPING, ContentType.PROGRESS}:
                    # Check if there's actual content (not just typing)
                    has_real_content = any(
                        hasattr(sc, 'content_type') and sc.content_type != ContentType.TYPING
                        for sc in chat_list_item.agent_message.structured_content
                    )
                    if not has_real_content:
                        content = "..."  # Placeholder for processing state

        # Determine primary content type for delegate selection
        # Priority: text > thinking > progress > tool_call > typing
        content_type = "text"
        if not chat_list_item.is_user and chat_list_item.agent_message:
            # Find the most relevant content type (excluding typing)
            type_priority = [
                ContentType.TEXT,
                ContentType.THINKING,
                ContentType.PROGRESS,
                ContentType.TOOL_CALL,
                ContentType.TYPING,
            ]
            for sc in chat_list_item.agent_message.structured_content:
                if hasattr(sc, 'content_type'):
                    ct = sc.content_type
                    if ct in type_priority and ct != ContentType.TYPING:
                        content_type = ct.value
                        break
            # Only use typing if there's nothing else
            if content_type == "text" and not content:
                for sc in chat_list_item.agent_message.structured_content:
                    if hasattr(sc, 'content_type') and sc.content_type == ContentType.TYPING:
                        content_type = "typing"
                        break

        # Serialize structured content
        structured_content = []
        if not chat_list_item.is_user and chat_list_item.agent_message:
            structured_content = cls._serialize_structured_content(
                chat_list_item.agent_message.structured_content
            )

        # Format start time and duration
        start_time = cls._format_start_time(timestamp)

        # Calculate duration
        duration = ""
        if chat_list_item.is_user:
            # User message: get end_timestamp from item metadata
            end_timestamp = chat_list_item.metadata.get('end_timestamp')
            if end_timestamp:
                duration = cls._format_duration(timestamp, end_timestamp)
        elif chat_list_item.agent_message:
            # Agent message: check for typing indicator and end timestamp
            has_typing = any(
                hasattr(sc, 'content_type') and sc.content_type == ContentType.TYPING
                for sc in chat_list_item.agent_message.structured_content
            )
            # Get end timestamp from metadata if available
            end_timestamp = None
            if chat_list_item.agent_message.metadata:
                end_timestamp = chat_list_item.agent_message.metadata.get('end_timestamp')

            # Only show duration if message is complete or has explicit end time
            if not has_typing or end_timestamp:
                duration = cls._format_duration(timestamp, end_timestamp)

        return {
            cls.MESSAGE_ID: chat_list_item.message_id,
            cls.SENDER_ID: chat_list_item.sender_id,
            cls.SENDER_NAME: chat_list_item.sender_name,
            cls.IS_USER: chat_list_item.is_user,
            cls.CONTENT: content,
            cls.AGENT_COLOR: chat_list_item.agent_color,
            cls.AGENT_ICON: chat_list_item.agent_icon,
            cls.CREW_METADATA: chat_list_item.crew_member_metadata,
            cls.STRUCTURED_CONTENT: structured_content,
            cls.CONTENT_TYPE: content_type,
            cls.IS_READ: True,
            cls.TIMESTAMP: timestamp,
            cls.DATE_GROUP: cls._get_date_group(timestamp),
            cls.START_TIME: start_time,
            cls.DURATION: duration,
        }

    @classmethod
    def from_agent_message(
        cls,
        agent_message: AgentMessage,
        agent_color: str = "#4a90e2",
        agent_icon: str = "🤖",
        crew_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Convert an AgentMessage to QML model item.

        Args:
            agent_message: AgentMessage instance
            agent_color: Display color for agent
            agent_icon: Display icon for agent
            crew_metadata: Additional crew member metadata

        Returns:
            Dictionary suitable for QML model
        """
        timestamp = None
        if agent_message.metadata:
            timestamp = agent_message.metadata.get('timestamp')

        # Determine primary content type
        content_type = "text"
        for sc in agent_message.structured_content:
            if sc.content_type != ContentType.TEXT:
                content_type = sc.content_type.value
                break

        structured_content = cls._serialize_structured_content(
            agent_message.structured_content
        )

        # Format start time and duration
        start_time = cls._format_start_time(timestamp)
        has_typing = any(
            hasattr(sc, 'content_type') and sc.content_type == ContentType.TYPING
            for sc in agent_message.structured_content
        )
        end_timestamp = None
        if agent_message.metadata:
            end_timestamp = agent_message.metadata.get('end_timestamp')
        duration = cls._format_duration(timestamp, end_timestamp) if (not has_typing or end_timestamp) else ""

        return {
            cls.MESSAGE_ID: agent_message.message_id,
            cls.SENDER_ID: agent_message.sender_id,
            cls.SENDER_NAME: agent_message.sender_name,
            cls.IS_USER: False,
            cls.CONTENT: "",  # Use structuredContent instead
            cls.AGENT_COLOR: agent_color,
            cls.AGENT_ICON: agent_icon,
            cls.CREW_METADATA: crew_metadata or {},
            cls.STRUCTURED_CONTENT: structured_content,
            cls.CONTENT_TYPE: content_type,
            cls.IS_READ: True,
            cls.TIMESTAMP: timestamp,
            cls.DATE_GROUP: cls._get_date_group(timestamp),
            cls.START_TIME: start_time,
            cls.DURATION: duration,
        }
