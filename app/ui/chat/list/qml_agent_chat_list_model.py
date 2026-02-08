"""QML-compatible model for agent chat list.

This module provides a QAbstractListModel that exposes chat data to QML,
with proper role names and automatic date grouping for separators.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, QObject, Slot, Property

from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_types import ContentType
from agent.chat.content import StructureContent

logger = logging.getLogger(__name__)


class QmlAgentChatListModel(QAbstractListModel):
    """QML-compatible model for chat messages.

    This model exposes chat message data to QML with proper role names
    and automatic date grouping for message separators.

    Messages are rendered using structured_content, where each content item
    is rendered by a corresponding QML widget based on its content_type.

    Roles exposed to QML:
    - messageId: Unique message identifier
    - senderId: Sender's identifier
    - senderName: Display name of sender
    - isUser: Whether message is from user
    - agentColor: Color for agent avatar
    - agentIcon: Icon for agent avatar
    - crewMetadata: Additional crew member metadata
    - structuredContent: List of structured content items (each rendered by QML widget)
    - contentType: Primary content type for delegate selection
    - isRead: Read status for user messages
    - timestamp: Message timestamp for date grouping
    - dateGroup: Date group key for section headers
    """

    # Role names for QML
    MESSAGE_ID = "messageId"
    SENDER_ID = "senderId"
    SENDER_NAME = "senderName"
    IS_USER = "isUser"
    AGENT_COLOR = "agentColor"
    AGENT_ICON = "agentIcon"
    CREW_METADATA = "crewMetadata"
    STRUCTURED_CONTENT = "structuredContent"
    CONTENT_TYPE = "contentType"
    IS_READ = "isRead"
    TIMESTAMP = "timestamp"
    DATE_GROUP = "dateGroup"

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._items: List[Dict[str, Any]] = []
        self._message_id_to_row: Dict[str, int] = {}

    def roleNames(self):
        """Return role names for QML binding."""
        from PySide6.QtCore import QByteArray
        return {
            Qt.UserRole + 1: QByteArray(self.MESSAGE_ID.encode()),
            Qt.UserRole + 2: QByteArray(self.SENDER_ID.encode()),
            Qt.UserRole + 3: QByteArray(self.SENDER_NAME.encode()),
            Qt.UserRole + 4: QByteArray(self.IS_USER.encode()),
            Qt.UserRole + 5: QByteArray(self.AGENT_COLOR.encode()),
            Qt.UserRole + 6: QByteArray(self.AGENT_ICON.encode()),
            Qt.UserRole + 7: QByteArray(self.CREW_METADATA.encode()),
            Qt.UserRole + 8: QByteArray(self.STRUCTURED_CONTENT.encode()),
            Qt.UserRole + 9: QByteArray(self.CONTENT_TYPE.encode()),
            Qt.UserRole + 10: QByteArray(self.IS_READ.encode()),
            Qt.UserRole + 11: QByteArray(self.TIMESTAMP.encode()),
            Qt.UserRole + 12: QByteArray(self.DATE_GROUP.encode()),
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
        """Update an existing item.

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
        index = self.index(row, 0)
        self.dataChanged.emit(index, index)
        return True

    def get_item(self, row: int) -> Optional[Dict[str, Any]]:
        """Get item at the specified row."""
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def get_row_by_message_id(self, message_id: str) -> Optional[int]:
        """Get row index for a message ID."""
        return self._message_id_to_row.get(message_id)

    def get_item_by_message_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get item by message ID."""
        row = self._message_id_to_row.get(message_id)
        if row is not None:
            return self.get_item(row)
        return None

    def clear(self) -> None:
        """Clear all items from the model."""
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

        Simplified version - passes structured_content directly to QML,
        letting QML render widgets based on content_type.

        Args:
            chat_list_item: ChatListItem instance

        Returns:
            Dictionary suitable for QML model
        """
        from app.ui.chat.list.agent_chat_list_items import ChatListItem
        from agent.chat.content import ContentType

        if not isinstance(chat_list_item, ChatListItem):
            return {}

        # Get timestamp from metadata
        timestamp = None
        if chat_list_item.agent_message and chat_list_item.agent_message.metadata:
            timestamp = chat_list_item.agent_message.metadata.get('timestamp')

        # For user messages, use user_content as a simple text content
        if chat_list_item.is_user:
            structured_content = [{
                "content_type": ContentType.TEXT.value,
                "data": {"text": chat_list_item.user_content}
            }]
        else:
            # For agent messages, serialize structured_content
            structured_content = cls._serialize_structured_content(
                chat_list_item.agent_message.structured_content
            )

        # Determine primary content type for delegate selection
        # Priority: error > thinking > progress > tool_call > text > typing
        content_type = "text"
        if not chat_list_item.is_user and chat_list_item.agent_message:
            type_priority = [
                ContentType.ERROR,
                ContentType.THINKING,
                ContentType.PROGRESS,
                ContentType.TOOL_CALL,
                ContentType.TEXT,
                ContentType.TYPING,
            ]
            for sc in chat_list_item.agent_message.structured_content:
                if hasattr(sc, 'content_type') and sc.content_type in type_priority:
                    content_type = sc.content_type.value
                    break

        return {
            cls.MESSAGE_ID: chat_list_item.message_id,
            cls.SENDER_ID: chat_list_item.sender_id,
            cls.SENDER_NAME: chat_list_item.sender_name,
            cls.IS_USER: chat_list_item.is_user,
            cls.AGENT_COLOR: chat_list_item.agent_color,
            cls.AGENT_ICON: chat_list_item.agent_icon,
            cls.CREW_METADATA: chat_list_item.crew_member_metadata,
            cls.STRUCTURED_CONTENT: structured_content,
            cls.CONTENT_TYPE: content_type,
            cls.IS_READ: True,
            cls.TIMESTAMP: timestamp,
            cls.DATE_GROUP: cls._get_date_group(timestamp),
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

        Simplified version - passes structured_content directly to QML,
        letting QML render widgets based on content_type.

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

        # Determine primary content type for delegate selection
        # Priority: error > thinking > progress > tool_call > text > typing
        content_type = "text"
        type_priority = [
            ContentType.ERROR,
            ContentType.THINKING,
            ContentType.PROGRESS,
            ContentType.TOOL_CALL,
            ContentType.TEXT,
            ContentType.TYPING,
        ]
        for sc in agent_message.structured_content:
            if hasattr(sc, 'content_type') and sc.content_type in type_priority:
                content_type = sc.content_type.value
                break

        structured_content = cls._serialize_structured_content(
            agent_message.structured_content
        )

        return {
            cls.MESSAGE_ID: agent_message.message_id,
            cls.SENDER_ID: agent_message.sender_id,
            cls.SENDER_NAME: agent_message.sender_name,
            cls.IS_USER: False,
            cls.AGENT_COLOR: agent_color,
            cls.AGENT_ICON: agent_icon,
            cls.CREW_METADATA: crew_metadata or {},
            cls.STRUCTURED_CONTENT: structured_content,
            cls.CONTENT_TYPE: content_type,
            cls.IS_READ: True,
            cls.TIMESTAMP: timestamp,
            cls.DATE_GROUP: cls._get_date_group(timestamp),
        }
