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
from typing import List, Dict, Any, Optional, Set, Tuple
from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, QObject, Slot, Property, QTimer, Signal

from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_types import ContentType
from agent.chat.content import StructureContent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level time-format caches
#
# _format_start_time and _get_date_group depend on "today", so we key them on
# (timestamp, today_date).  The caches are dicts that are cleared whenever the
# calendar date changes.  _format_duration is cached only when both endpoints
# are known (end_timestamp is not None); open-ended durations must not be cached.
# ---------------------------------------------------------------------------
_today_cache_key: Optional[Any] = None   # last seen date.today()
_start_time_cache: Dict[Tuple, str] = {}
_date_group_cache: Dict[Tuple, str] = {}
_duration_cache: Dict[Tuple, str] = {}   # keyed on (start, end) – end is never None


def _invalidate_time_caches_if_needed() -> Any:
    """Clear date-sensitive caches when the calendar day has rolled over."""
    global _today_cache_key, _start_time_cache, _date_group_cache
    today = datetime.now().date()
    if today != _today_cache_key:
        _today_cache_key = today
        _start_time_cache.clear()
        _date_group_cache.clear()
    return today


def _get_date_group(timestamp) -> str:
    """Get date group key for message separators (module-level, thread-safe)."""
    if not timestamp:
        return ""

    today = _invalidate_time_caches_if_needed()
    cache_key = (timestamp, today)
    cached = _date_group_cache.get(cache_key)
    if cached is not None:
        return cached

    if isinstance(timestamp, str):
        try:
            msg_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            try:
                msg_date = datetime.fromtimestamp(float(timestamp))
            except (ValueError, TypeError):
                logger.debug(f"Could not parse timestamp: {timestamp}")
                return ""
    elif isinstance(timestamp, (int, float)):
        msg_date = datetime.fromtimestamp(timestamp)
    else:
        return ""

    yesterday = today - timedelta(days=1)
    this_week_start = today - timedelta(days=today.weekday())
    last_week_start = this_week_start - timedelta(days=7)
    this_month_start = today.replace(day=1)
    msg_date_only = msg_date.date()

    if msg_date_only == today:
        result = "Today"
    elif msg_date_only == yesterday:
        result = "Yesterday"
    elif msg_date_only >= this_week_start:
        result = "This Week"
    elif msg_date_only >= last_week_start:
        result = "Last Week"
    elif msg_date_only >= this_month_start:
        result = "This Month"
    else:
        result = msg_date.strftime("%B %Y")

    _date_group_cache[cache_key] = result
    return result


def _format_start_time(timestamp) -> str:
    """Format timestamp as start time with date context (module-level, thread-safe)."""
    if not timestamp:
        return ""

    today = _invalidate_time_caches_if_needed()
    cache_key = (timestamp, today)
    cached = _start_time_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        if isinstance(timestamp, str):
            msg_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif isinstance(timestamp, (int, float)):
            msg_date = datetime.fromtimestamp(timestamp)
        else:
            return ""

        msg_date_only = msg_date.date()
        if msg_date_only == today:
            result = msg_date.strftime("%H:%M")
        elif msg_date_only == today - timedelta(days=1):
            result = f"昨天 {msg_date.strftime('%H:%M')}"
        elif msg_date.year == today.year:
            result = msg_date.strftime("%m-%d %H:%M")
        else:
            result = msg_date.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        result = ""

    _start_time_cache[cache_key] = result
    return result


def _format_duration(start_timestamp, end_timestamp=None) -> str:
    """Format duration between timestamps (module-level, thread-safe)."""
    if not start_timestamp:
        return ""

    if end_timestamp is not None:
        cache_key = (start_timestamp, end_timestamp)
        cached = _duration_cache.get(cache_key)
        if cached is not None:
            return cached

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
            result = ""
        elif total_seconds < 60:
            result = f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            result = f"{minutes}m {seconds}s" if seconds else f"{minutes}m"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            result = f"{hours}h {minutes}m" if minutes else f"{hours}h"

    except (ValueError, TypeError):
        result = ""

    if end_timestamp is not None:
        _duration_cache[(start_timestamp, end_timestamp)] = result
    return result


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
    CREW_READ_BY = "crewReadBy"  # List of crew members who read this message (router)

    # Signal emitted after a batch of updates is flushed to QML
    batchFlushed = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._items: List[Dict[str, Any]] = []
        # _message_id_to_row stores a "virtual" row index that has no direct
        # relationship to the physical list position until adjusted by the
        # cumulative prepend offset.
        #
        # Invariant:  real_row = stored_value - _prepend_offset
        #             stored_value = real_row + _prepend_offset
        #
        # When prepend_items(count) is called we want every existing real_row
        # to increase by count.  Because stored values are unchanged we just
        # increment _prepend_offset by count — O(1) instead of O(N).
        self._message_id_to_row: Dict[str, int] = {}
        self._prepend_offset: int = 0

        # Pre-built role name cache for data() to avoid roleNames() + decode on every access
        self._role_name_cache: Dict[int, str] = {}
        for role, name_bytes in self.roleNames().items():
            self._role_name_cache[role] = name_bytes.data().decode()

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
            Qt.UserRole + 16: QByteArray(self.CREW_READ_BY.encode()),
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

        role_name = self._role_name_cache.get(role)
        if role_name:
            return self._items[row].get(role_name)

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
            self._message_id_to_row[item[self.MESSAGE_ID]] = row + self._prepend_offset
        self.endInsertRows()
        return row

    def add_items_batch(self, items: List[Dict[str, Any]]) -> int:
        """Append multiple items in a single beginInsertRows/endInsertRows call.

        Compared to calling add_item() N times this emits only one rowsInserted
        signal, which is significantly faster when loading history pages.

        Args:
            items: List of message dictionaries to append

        Returns:
            Row index of the first inserted item, or -1 if items is empty
        """
        if not items:
            return -1
        first_row = len(self._items)
        last_row = first_row + len(items) - 1
        self.beginInsertRows(QModelIndex(), first_row, last_row)
        for i, item in enumerate(items):
            self._items.append(item)
            msg_id = item.get(self.MESSAGE_ID)
            if msg_id:
                self._message_id_to_row[msg_id] = first_row + i + self._prepend_offset
        self.endInsertRows()
        return first_row

    def prepend_items(self, items: List[Dict[str, Any]]) -> int:
        """Insert items at the beginning of the model.

        Only updates the index for new items and offsets existing entries by
        ``count`` – avoids a full rebuild of ``_message_id_to_row``.

        Args:
            items: List of message dictionaries to prepend

        Returns:
            Number of items prepended
        """
        if not items:
            return 0
        count = len(items)
        self.beginInsertRows(QModelIndex(), 0, count - 1)

        # Shift every existing entry O(1): decrement offset so that for each
        # existing stored value s:  real_new = s - offset_new
        #                                    = s - (offset_old - count)
        #                                    = (s - offset_old) + count   ✓
        self._prepend_offset -= count

        # New items sit at real rows 0 … count-1.
        # stored = real + offset_new = i + self._prepend_offset  (after decrement)
        self._items = list(items) + self._items
        for i, item in enumerate(items):
            msg_id = item.get(self.MESSAGE_ID)
            if msg_id:
                self._message_id_to_row[msg_id] = i + self._prepend_offset

        self.endInsertRows()
        return count

    def remove_first_n(self, n: int) -> None:
        """Remove first n items from the model."""
        total = len(self._items)
        if n <= 0 or n > total:
            return
        self.beginRemoveRows(QModelIndex(), 0, n - 1)
        for i in range(n):
            msg_id = self._items[i].get(self.MESSAGE_ID)
            if msg_id:
                self._message_id_to_row.pop(msg_id, None)
        self._items = self._items[n:]
        # Advance the offset so every remaining stored value still maps to the
        # correct (now-shifted) real row index.
        self._prepend_offset += n
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
        stored = self._message_id_to_row.get(message_id)
        if stored is None:
            return False

        row = stored - self._prepend_offset
        if row < 0 or row >= len(self._items):
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
        stored = self._message_id_to_row.get(message_id)
        if stored is None:
            return None
        row = stored - self._prepend_offset
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def get_row_by_message_id(self, message_id: str) -> Optional[int]:
        """Get row index for a message ID."""
        stored = self._message_id_to_row.get(message_id)
        if stored is None:
            return None
        return stored - self._prepend_offset

    def clear(self) -> None:
        """Clear all items from the model."""
        # Stop any pending batch updates
        self._batch_timer.stop()
        self._dirty_rows.clear()

        self.beginResetModel()
        self._items = []
        self._message_id_to_row = {}
        self._prepend_offset = 0
        self.endResetModel()

    @staticmethod
    def _get_date_group(timestamp) -> str:
        return _get_date_group(timestamp)

    @staticmethod
    def _format_start_time(timestamp) -> str:
        return _format_start_time(timestamp)

    @staticmethod
    def _format_duration(start_timestamp, end_timestamp=None) -> str:
        return _format_duration(start_timestamp, end_timestamp)

    @staticmethod
    def _serialize_structured_content(structured_content: List[StructureContent]) -> List[Dict[str, Any]]:
        """Convert structured content to QML-compatible format.

        Text items are passed through with their raw text intact.
        Code-block splitting is deferred to QML (StructuredContentRenderer)
        so it only runs for visible delegates, not for every model update.
        """
        result = []
        for sc in structured_content:
            if hasattr(sc, 'to_dict'):
                d = sc.to_dict()
            else:
                d = {
                    'content_type': getattr(sc, 'content_type', 'text'),
                    'data': getattr(sc, 'data', {})
                }
            result.append(d)
        return result

    @classmethod
    def from_chat_list_item(cls, chat_list_item: 'ChatListItem') -> Dict[str, Any]:
        """Convert a ChatListItem to a QML model dict.

        Delegates to MessageConverter which is safe to call from background
        threads (no Qt objects touched).
        """
        from app.ui.chat.list.builders.message_converter import MessageConverter
        return MessageConverter.from_chat_list_item(chat_list_item)

    @classmethod
    def from_agent_message(
        cls,
        agent_message: AgentMessage,
        agent_color: str = "#4a90e2",
        agent_icon: str = "🤖",
        crew_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convert an AgentMessage to a QML model dict.

        Delegates to MessageConverter which is safe to call from background
        threads (no Qt objects touched).
        """
        from app.ui.chat.list.builders.message_converter import MessageConverter
        return MessageConverter.from_agent_message(
            agent_message, agent_color, agent_icon, crew_metadata
        )
