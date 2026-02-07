"""Model for agent chat list using QAbstractListModel.

This module provides the list model that manages chat message items
for the QListView in the agent chat list component.
"""

from typing import List, Dict, Optional

from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex

from app.ui.chat.list.agent_chat_list_items import ChatListItem


class AgentChatListModel(QAbstractListModel):
    """Model for chat message items in the agent chat list.

    This model manages a list of ChatListItem objects and provides
    efficient access through row indices and message IDs.

    Attributes:
        ITEM_ROLE: Custom role for accessing the full ChatListItem
        MESSAGE_ID_ROLE: Custom role for accessing just the message_id
    """

    ITEM_ROLE = Qt.UserRole + 1
    MESSAGE_ID_ROLE = Qt.UserRole + 2

    def __init__(self, parent=None):
        """Initialize the model with empty item list.

        Args:
            parent: Parent QObject for memory management
        """
        super().__init__(parent)
        self._items: List[ChatListItem] = []
        self._message_id_to_row: Dict[str, int] = {}

    def rowCount(self, parent: QModelIndex = None) -> int:
        """Return the number of rows in the model.

        Args:
            parent: Parent index (not used, always returns 0 if valid)

        Returns:
            Number of items in the model
        """
        if parent is None:
            parent = QModelIndex()
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        """Return data for the given index and role.

        Args:
            index: Model index to get data from
            role: Role to retrieve (DisplayRole, ITEM_ROLE, MESSAGE_ID_ROLE)

        Returns:
            Data for the requested role, or None if not available
        """
        if not index.isValid():
            return None
        item = self._items[index.row()]
        if role == self.ITEM_ROLE:
            return item
        if role == self.MESSAGE_ID_ROLE:
            return item.message_id
        if role == Qt.DisplayRole:
            if item.is_user:
                return item.user_content
            if item.agent_message:
                return item.agent_message.get_text_content()
        return None

    def add_item(self, item: ChatListItem) -> int:
        """Add a single item to the end of the model.

        Args:
            item: ChatListItem to add

        Returns:
            Row index where the item was added
        """
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(item)
        if item.message_id:
            self._message_id_to_row[item.message_id] = row
        self.endInsertRows()
        return row

    def prepend_items(self, items: List[ChatListItem]) -> int:
        """Insert items at the beginning of the model.

        After insertion, all existing row indices shift by len(items).
        The id-to-row map is rebuilt entirely for correctness.

        Args:
            items: List of ChatListItem objects to prepend

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
            if item.message_id:
                self._message_id_to_row[item.message_id] = i
        self.endInsertRows()
        return count

    def remove_first_n(self, n: int) -> None:
        """Remove first n items from the model.

        Args:
            n: Number of items to remove from the beginning
        """
        total = len(self._items)
        if n <= 0 or n > total:
            return
        self.beginRemoveRows(QModelIndex(), 0, n - 1)
        self._items = self._items[n:]
        # Rebuild index map
        self._message_id_to_row.clear()
        for i, item in enumerate(self._items):
            if item.message_id:
                self._message_id_to_row[item.message_id] = i
        self.endRemoveRows()

    def remove_last_n(self, n: int) -> None:
        """Remove last n items from the model.

        Args:
            n: Number of items to remove from the end
        """
        total = len(self._items)
        if n <= 0 or n > total:
            return
        start = total - n
        self.beginRemoveRows(QModelIndex(), start, total - 1)
        removed = self._items[start:]
        self._items = self._items[:start]
        for item in removed:
            if item.message_id:
                self._message_id_to_row.pop(item.message_id, None)
        self.endRemoveRows()

    def get_item(self, row: int) -> Optional[ChatListItem]:
        """Get item at the specified row.

        Args:
            row: Row index

        Returns:
            ChatListItem at the row, or None if row is invalid
        """
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def get_row_by_message_id(self, message_id: str) -> Optional[int]:
        """Get row index for a message ID.

        Args:
            message_id: Message ID to find

        Returns:
            Row index, or None if not found
        """
        return self._message_id_to_row.get(message_id)

    def get_item_by_message_id(self, message_id: str) -> Optional[ChatListItem]:
        """Get item by its message ID.

        Args:
            message_id: Message ID to find

        Returns:
            ChatListItem with the message ID, or None if not found
        """
        row = self.get_row_by_message_id(message_id)
        if row is None:
            return None
        return self._items[row]

    def notify_row_changed(self, row: int) -> None:
        """Notify that data at the given row has changed.

        Args:
            row: Row index that changed
        """
        if row < 0 or row >= len(self._items):
            return
        index = self.index(row, 0)
        self.dataChanged.emit(index, index)

    def clear(self) -> None:
        """Clear all items from the model."""
        self.beginResetModel()
        self._items = []
        self._message_id_to_row = {}
        self.endResetModel()
