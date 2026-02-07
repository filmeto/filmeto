"""Agent chat list component using QListView for virtualized rendering.

Optimized to leverage FastMessageHistoryService capabilities:
- Message grouping by message_id for unified display
- Page-based initial loading with unique message count
- Efficient pagination using line offsets
- Smart polling using active log count only
- Virtualized widget management for performance
- Cached history instance for reduced overhead
"""

import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple, TYPE_CHECKING

from PySide6.QtWidgets import (
    QVBoxLayout, QWidget, QListView, QStyledItemDelegate, QAbstractItemView,
    QStyleOptionViewItem, QSizePolicy
)
from PySide6.QtCore import (
    Qt, Signal, Slot, QTimer, QAbstractListModel, QModelIndex, QSize, QPoint
)

from agent import AgentMessage
from app.ui.base_widget import BaseWidget
from utils.i18n_utils import tr
from agent.chat.history.agent_chat_history_service import FastMessageHistoryService
from agent.chat.history.agent_chat_storage import MessageLogHistory

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.data.workspace import Workspace


@dataclass
class ChatListItem:
    message_id: str
    sender_id: str
    sender_name: str
    is_user: bool
    user_content: str = ""
    agent_message: Optional[AgentMessage] = None
    agent_color: str = "#4a90e2"
    agent_icon: str = "🤖"
    crew_member_metadata: Dict[str, Any] = field(default_factory=dict)


class MessageGroup:
    """Helper class to group messages by message_id and combine content."""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.all_content: List[Dict[str, Any]] = []

    def add_message(self, msg_data: Dict[str, Any]) -> None:
        """Add a message to the group."""
        self.messages.append(msg_data)
        content_list = msg_data.get("content", [])
        if isinstance(content_list, list):
            self.all_content.extend(content_list)

    def get_combined_message(self) -> Optional[Dict[str, Any]]:
        """Get the combined message with all content items."""
        if not self.messages:
            return None

        # Use the first message as the base
        base_msg = dict(self.messages[0])

        # Combine all content items
        base_msg["content"] = self.all_content

        return base_msg


@dataclass
class LoadState:
    """Track the current loading state for efficient pagination."""
    active_log_count: int = 0  # Number of lines in active log
    unique_message_count: int = 0  # Number of unique messages in model
    current_line_offset: int = 0  # Current line offset in active log
    has_more_older: bool = True  # Whether there are more older messages
    known_message_ids: set = field(default_factory=set)  # Track known message IDs


class AgentChatListModel(QAbstractListModel):
    ITEM_ROLE = Qt.UserRole + 1
    MESSAGE_ID_ROLE = Qt.UserRole + 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[ChatListItem] = []
        self._message_id_to_row: Dict[str, int] = {}

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
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

    def remove_first_n(self, n: int):
        """Remove first n items from the model."""
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

    def remove_last_n(self, n: int):
        """Remove last n items from the model."""
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
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def get_row_by_message_id(self, message_id: str) -> Optional[int]:
        return self._message_id_to_row.get(message_id)

    def get_item_by_message_id(self, message_id: str) -> Optional[ChatListItem]:
        row = self.get_row_by_message_id(message_id)
        if row is None:
            return None
        return self._items[row]

    def notify_row_changed(self, row: int):
        if row < 0 or row >= len(self._items):
            return
        index = self.index(row, 0)
        self.dataChanged.emit(index, index)

    def clear(self):
        self.beginResetModel()
        self._items = []
        self._message_id_to_row = {}
        self.endResetModel()


class AgentChatListDelegate(QStyledItemDelegate):
    def __init__(self, owner: "AgentChatListWidget", parent=None):
        super().__init__(parent)
        self._owner = owner

    def sizeHint(self, option, index):
        return self._owner.get_item_size_hint(option, index)

    def paint(self, painter, option, index):
        return


class AgentChatListView(QListView):
    viewport_scrolled = Signal()
    viewport_resized = Signal()

    def scrollContentsBy(self, dx: int, dy: int):
        super().scrollContentsBy(dx, dy)
        self.viewport_scrolled.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.viewport_resized.emit()


class AgentChatListWidget(BaseWidget):
    """Virtualized chat list widget for agent conversations.

    Loads data exclusively from AgentChatHistory:
    - Initial load: PAGE_SIZE most recent messages
    - Scroll to top: loads older messages in pages
    - At bottom: polls for new messages via revision counter

    Performance optimizations:
    - Cached row positions for fast visible range calculation
    - Throttled scroll event handling
    - Deferred widget creation for smooth scrolling
    """

    # Configuration
    PAGE_SIZE = 30
    MAX_MODEL_ITEMS = 300
    NEW_DATA_CHECK_INTERVAL_MS = 500
    SCROLL_TOP_THRESHOLD = 50
    SCROLL_BOTTOM_THRESHOLD = 50

    # Performance tuning
    VISIBLE_REFRESH_DELAY_MS = 16  # ~60fps
    SCROLL_THROTTLE_MS = 50  # Throttle scroll events
    MAX_VISIBLE_WIDGETS = 30  # Limit widgets created at once

    # Signals
    reference_clicked = Signal(str, str)  # ref_type, ref_id
    message_complete = Signal(str, str)  # message_id, agent_name
    load_more_requested = Signal()

    def __init__(self, workspace: "Workspace", parent=None):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        self._model = AgentChatListModel(self)
        self._delegate = AgentChatListDelegate(self, self)
        self._visible_widgets: Dict[int, QWidget] = {}
        self._size_hint_cache: Dict[str, Dict[int, QSize]] = {}

        # Cached row positions for performance: {row: (y_position, height)}
        self._row_positions_cache: Dict[int, Tuple[int, int]] = {}
        self._total_height_cache: int = 0
        self._positions_cache_dirty: bool = True

        self._scroll_timer = QTimer(self)
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.timeout.connect(self._scroll_to_bottom)

        self._visible_refresh_timer = QTimer(self)
        self._visible_refresh_timer.setSingleShot(True)
        self._visible_refresh_timer.timeout.connect(self._refresh_visible_widgets)

        # Throttle for scroll events
        self._scroll_throttle_timer = QTimer(self)
        self._scroll_throttle_timer.setSingleShot(True)
        self._scroll_throttle_timer.timeout.connect(self._on_scroll_throttled)
        self._pending_scroll_value: Optional[int] = None
        self._scroll_delta_since_last_refresh = 0

        # New data check timer - polls for new messages using active log count
        self._new_data_check_timer = QTimer(self)
        self._new_data_check_timer.timeout.connect(self._check_for_new_data)

        self._user_at_bottom = True
        self._bottom_reached = False

        self._crew_member_metadata: Dict[str, Dict[str, Any]] = {}
        self._agent_current_cards: Dict[str, str] = {}

        # Optimized loading state using LoadState dataclass
        self._load_state = LoadState()
        self._loading_older = False

        # Cache history instance for reduced overhead
        self._history: Optional[MessageLogHistory] = None

        self._setup_ui()
        self._load_crew_member_metadata()
        self._load_recent_conversation()
        self._start_new_data_check_timer()

    def _get_history(self) -> Optional[MessageLogHistory]:
        """Get or create cached history instance."""
        if self._history is None:
            workspace_path = self.workspace.workspace_path
            project_name = self.workspace.project_name
            if workspace_path and project_name:
                self._history = FastMessageHistoryService.get_history(
                    workspace_path, project_name
                )
        return self._history

    def on_project_switched(self, project_name: str):
        self.refresh_crew_member_metadata()
        # Reset loading state
        self._load_state = LoadState()
        self._loading_older = False
        # Invalidate history cache
        self._history = None
        # Clear position cache
        self._positions_cache_dirty = True
        self._row_positions_cache.clear()
        self._load_recent_conversation()

    def refresh_crew_member_metadata(self):
        self._load_crew_member_metadata()

    def _invalidate_positions_cache(self):
        """Mark the positions cache as dirty - needs rebuild."""
        self._positions_cache_dirty = True

    def _rebuild_positions_cache(self):
        """Rebuild the row positions cache from scratch."""
        if not self._positions_cache_dirty:
            return

        self._row_positions_cache.clear()
        current_y = 0
        row_count = self._model.rowCount()

        for row in range(row_count):
            index = self._model.index(row, 0)
            from PySide6.QtWidgets import QStyleOptionViewItem
            option = QStyleOptionViewItem()
            option.rect = self.list_view.viewport().rect()
            size = self.get_item_size_hint(option, index)

            self._row_positions_cache[row] = (current_y, size.height())
            current_y += size.height()

        self._total_height_cache = current_y
        self._positions_cache_dirty = False

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)

        self.list_view = AgentChatListView(self)
        self.list_view.setModel(self._model)
        self.list_view.setItemDelegate(self._delegate)
        self.list_view.setUniformItemSizes(False)
        self.list_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_view.setSelectionMode(QAbstractItemView.NoSelection)
        self.list_view.setFocusPolicy(Qt.NoFocus)
        self.list_view.setSpacing(8)
        self.list_view.setViewportMargins(5, 10, 5, 10)
        self.list_view.setStyleSheet("""
            QListView {
                background-color: #252525;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2b2d30;
                width: 10px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #505254;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #606264;
            }
        """)

        self.list_view.verticalScrollBar().valueChanged.connect(self._on_scroll_value_changed)
        self.list_view.viewport_scrolled.connect(self._schedule_visible_refresh)
        self.list_view.viewport_resized.connect(self._on_viewport_resized)

        self._model.rowsInserted.connect(self._on_rows_inserted)
        self._model.dataChanged.connect(self._on_model_data_changed)
        self._model.modelReset.connect(self._clear_visible_widgets)

        layout.addWidget(self.list_view)

    # ─── Data loading from AgentChatHistory ───────────────────────────

    def _load_recent_conversation(self):
        """Load recent conversation from history using optimized grouping."""
        try:
            project = self.workspace.get_project()
            if not project:
                logger.warning("No project found, skipping history load")
                return

            history = self._get_history()
            if not history:
                logger.warning("Could not get history instance")
                return

            logger.info(f"Loading history using cached instance")

            # Get latest messages from active log
            raw_messages = history.get_latest_messages(count=self.PAGE_SIZE)
            logger.info(f"Retrieved {len(raw_messages)} raw messages from active log")

            # Update load state
            self._load_state.active_log_count = history.storage.get_message_count()
            self._load_state.current_line_offset = self._load_state.active_log_count

            if raw_messages:
                # Clear model and caches
                self._model.clear()
                self._size_hint_cache.clear()
                self._clear_visible_widgets()
                self._load_state.known_message_ids.clear()

                # Group messages by message_id using MessageGroup helper
                message_groups: Dict[str, MessageGroup] = {}
                for msg_data in raw_messages:
                    message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
                    if not message_id:
                        continue

                    if message_id not in message_groups:
                        message_groups[message_id] = MessageGroup()
                    message_groups[message_id].add_message(msg_data)

                # Convert groups to ordered list (maintaining chronological order)
                # raw_messages are in reverse chronological (newest first), so reverse
                ordered_messages = []
                for msg_data in reversed(raw_messages):
                    message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
                    if message_id in message_groups and message_id not in self._load_state.known_message_ids:
                        combined = message_groups[message_id].get_combined_message()
                        if combined:
                            ordered_messages.append(combined)
                            self._load_state.known_message_ids.add(message_id)

                # Load messages into model
                for msg_data in ordered_messages:
                    self._load_message_from_history(msg_data)

                # Update load state
                self._load_state.unique_message_count = len(ordered_messages)
                self._load_state.has_more_older = len(raw_messages) >= self.PAGE_SIZE

                # Get total count (including archives)
                total_count = history.get_total_count()

                logger.info(
                    f"Loaded {len(ordered_messages)} unique messages "
                    f"(from {len(raw_messages)} raw messages, "
                    f"total available: {total_count})"
                )

                # Scroll to bottom after loading
                self._schedule_scroll()
                QTimer.singleShot(100, self._ensure_widgets_visible_and_scrolled)
            else:
                self._model.clear()
                self._size_hint_cache.clear()
                self._clear_visible_widgets()
                self._load_state.known_message_ids.clear()
                self._load_state.unique_message_count = 0
                self._load_state.has_more_older = False
                logger.info("No messages found in history")

        except Exception as e:
            logger.error(f"Error loading recent conversation: {e}", exc_info=True)

    def _load_older_messages(self):
        """Load older messages when user scrolls to the top."""
        if self._loading_older or not self._load_state.has_more_older:
            return

        self._loading_older = True
        try:
            history = self._get_history()
            if not history:
                return

            # Get messages before current offset
            current_offset = self._load_state.current_line_offset
            older_messages = history.get_messages_before(
                current_offset, count=self.PAGE_SIZE
            )

            if not older_messages:
                self._load_state.has_more_older = False
                return

            # Save current scroll state for position restoration
            scrollbar = self.list_view.verticalScrollBar()
            old_max = scrollbar.maximum()
            old_value = scrollbar.value()

            # Group messages by message_id using MessageGroup helper
            message_groups: Dict[str, MessageGroup] = {}
            for msg_data in older_messages:
                message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
                if not message_id:
                    continue

                if message_id not in message_groups:
                    message_groups[message_id] = MessageGroup()
                message_groups[message_id].add_message(msg_data)

            # Build items from grouped history data (already in chronological order)
            items = []
            for message_id, group in message_groups.items():
                # Check if already known
                if message_id in self._load_state.known_message_ids:
                    continue

                combined_msg = group.get_combined_message()
                if combined_msg:
                    item = self._build_item_from_history(combined_msg)
                    if item:
                        items.append(item)
                        self._load_state.known_message_ids.add(message_id)

            if items:
                # Clear visible widgets before prepending (rows will shift)
                self._clear_visible_widgets()

                # Prepend items to model
                self._model.prepend_items(items)

                # Update load state
                self._load_state.unique_message_count += len(items)
                self._load_state.current_line_offset = current_offset - len(older_messages)

                # Restore scroll position so the view doesn't jump
                QTimer.singleShot(0, lambda: self._restore_scroll_after_prepend(
                    scrollbar, old_max, old_value
                ))

                # Prune oldest items if model exceeds MAX_MODEL_ITEMS
                self._prune_model_bottom()

                logger.debug(f"Prepended {len(items)} older unique messages (from {len(older_messages)} raw messages)")

            # Check if we've loaded all available messages
            if len(older_messages) < self.PAGE_SIZE:
                self._load_state.has_more_older = False

        except Exception as e:
            logger.error(f"Error loading older messages: {e}", exc_info=True)
        finally:
            self._loading_older = False

    def _restore_scroll_after_prepend(self, scrollbar, old_max: int, old_value: int):
        """Restore scroll position after prepending items to keep the view stable."""
        new_max = scrollbar.maximum()
        delta = new_max - old_max
        scrollbar.setValue(old_value + delta)
        self._schedule_visible_refresh()

    def _prune_model_bottom(self):
        """Remove excess items from the bottom of the model if it exceeds MAX_MODEL_ITEMS."""
        excess = self._model.rowCount() - self.MAX_MODEL_ITEMS
        if excess > 0:
            self._clear_visible_widgets()
            # Remove items from model
            for _ in range(excess):
                if self._model.rowCount() > 0:
                    item = self._model.get_item(self._model.rowCount() - 1)
                    if item and item.message_id in self._load_state.known_message_ids:
                        self._load_state.known_message_ids.remove(item.message_id)
                    self._model.remove_last_n(1)
            self._user_at_bottom = False

    def _prune_model_top(self):
        """Remove excess items from the top of the model if it exceeds MAX_MODEL_ITEMS."""
        excess = self._model.rowCount() - self.MAX_MODEL_ITEMS
        if excess > 0:
            self._clear_visible_widgets()
            # Remove items from model
            for _ in range(excess):
                if self._model.rowCount() > 0:
                    item = self._model.get_item(0)
                    if item and item.message_id in self._load_state.known_message_ids:
                        self._load_state.known_message_ids.remove(item.message_id)
                    self._model.remove_first_n(1)
            self._load_state.has_more_older = True

    # ─── New data polling ─────────────────────────────────────────────

    def _start_new_data_check_timer(self):
        """Start the timer to check for new data."""
        self._new_data_check_timer.start(self.NEW_DATA_CHECK_INTERVAL_MS)

    def _stop_new_data_check_timer(self):
        """Stop the new data check timer."""
        self._new_data_check_timer.stop()

    def _check_for_new_data(self):
        """Check for new data by comparing active log count (fast, no disk I/O)."""
        if not self._user_at_bottom:
            return

        try:
            history = self._get_history()
            if not history:
                return

            # Use active log count for fast checking (O(1) cached value)
            current_count = history.storage.get_message_count()

            # Initialize on first check
            if self._load_state.active_log_count == 0:
                self._load_state.active_log_count = current_count
                return

            # Check if new messages were added to active log
            if current_count > self._load_state.active_log_count:
                self._load_state.active_log_count = current_count
                self._load_new_messages_from_history()

        except Exception as e:
            logger.error(f"Error checking for new data: {e}")

    def _load_new_messages_from_history(self):
        """Load new messages from history that aren't in the model yet."""
        try:
            history = self._get_history()
            if not history:
                return

            # Get messages after current offset
            current_offset = self._load_state.current_line_offset
            new_messages = history.get_messages_after(current_offset, count=100)

            if not new_messages:
                return

            # Group messages by message_id using MessageGroup helper
            message_groups: Dict[str, MessageGroup] = {}
            for msg_data in new_messages:
                message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
                if not message_id:
                    continue

                if message_id not in message_groups:
                    message_groups[message_id] = MessageGroup()
                message_groups[message_id].add_message(msg_data)

            # Add only unknown messages
            added_count = 0
            for message_id, group in message_groups.items():
                # Only add if not already known
                if message_id not in self._load_state.known_message_ids:
                    combined_msg = group.get_combined_message()
                    if combined_msg:
                        self._load_message_from_history(combined_msg)
                        self._load_state.known_message_ids.add(message_id)
                        added_count += 1

            # Update load state
            self._load_state.current_line_offset = current_offset + len(new_messages)
            self._load_state.unique_message_count += added_count

            if added_count > 0:
                # Prune oldest items if model exceeds MAX_MODEL_ITEMS
                self._prune_model_top()
                self._schedule_scroll()
                logger.debug(f"Loaded {added_count} new unique messages (from {len(new_messages)} raw messages)")

        except Exception as e:
            logger.error(f"Error loading new messages: {e}", exc_info=True)

    # ─── Message item building ────────────────────────────────────────

    def _build_item_from_history(self, msg_data: Dict[str, Any]) -> Optional[ChatListItem]:
        """Build a ChatListItem from history data without adding to model."""
        try:
            from agent.chat.agent_chat_message import AgentMessage as ChatAgentMessage
            from agent.chat.agent_chat_types import MessageType
            from agent.chat.content import StructureContent

            metadata = msg_data.get("metadata", {})
            content_list = msg_data.get("content", [])

            message_id = metadata.get("message_id", "")
            sender_id = metadata.get("sender_id", "unknown")
            sender_name = metadata.get("sender_name", sender_id)
            message_type_str = metadata.get("message_type", "text")

            if not message_id:
                logger.warning(f"No message_id in msg_data: {msg_data}")
                return None

            try:
                message_type = MessageType(message_type_str)
            except ValueError:
                logger.debug(f"Unknown message type '{message_type_str}', using TEXT")
                message_type = MessageType.TEXT

            is_user = sender_id.lower() == "user"

            if is_user:
                text_content = ""
                for content_item in content_list:
                    if isinstance(content_item, dict):
                        if content_item.get("content_type") == "text":
                            text_content = content_item.get("data", {}).get("text", "")
                            break

                return ChatListItem(
                    message_id=message_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    is_user=True,
                    user_content=text_content,
                )
            else:
                structured_content = []
                for content_item in content_list:
                    if isinstance(content_item, dict):
                        try:
                            sc = StructureContent.from_dict(content_item)
                            structured_content.append(sc)
                        except Exception as e:
                            logger.debug(f"Failed to load structured content item: {e}")

                agent_message = ChatAgentMessage(
                    message_type=message_type,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    message_id=message_id,
                    metadata=metadata,
                    structured_content=structured_content,
                )

                agent_color, agent_icon, crew_member_data = self._resolve_agent_metadata(
                    sender_name, metadata
                )

                return ChatListItem(
                    message_id=message_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    is_user=False,
                    agent_message=agent_message,
                    agent_color=agent_color,
                    agent_icon=agent_icon,
                    crew_member_metadata=crew_member_data,
                )

        except Exception as e:
            logger.error(f"Error building item from history: {e}", exc_info=True)
            return None

    def _load_message_from_history(self, msg_data: Dict[str, Any]):
        """Load a single message from history data into the model."""
        item = self._build_item_from_history(msg_data)
        if item:
            self._model.add_item(item)
        else:
            logger.warning(f"Failed to build item from msg_data: {msg_data.get('message_id', 'unknown')}")

    # ─── Crew member metadata ────────────────────────────────────────

    def _load_crew_member_metadata(self):
        try:
            from agent.crew.crew_service import CrewService

            project = self.workspace.get_project()
            if project:
                crew_member_service = CrewService()
                crew_members = crew_member_service.get_project_crew_members(project)
                self._crew_member_metadata = {}
                for name, crew_member in crew_members.items():
                    self._crew_member_metadata[crew_member.config.name.lower()] = crew_member
            else:
                self._crew_member_metadata = {}
        except Exception as e:
            print(f"Error loading crew members: {e}")
            self._crew_member_metadata = {}

    def _get_sender_info(self, sender: str):
        normalized_sender = sender.lower()
        is_user = normalized_sender in [tr("用户").lower(), "用户", "user", tr("user").lower()]
        is_system = normalized_sender in [tr("系统").lower(), "系统", "system", tr("system").lower()]
        is_tool = normalized_sender in [tr("工具").lower(), "工具", "tool", tr("tool").lower()]
        is_assistant = normalized_sender in [tr("助手").lower(), "助手", "assistant", tr("assistant").lower()]

        if is_user:
            icon_char = "\ue6b3"
            alignment = Qt.AlignRight
        elif is_system or is_tool:
            icon_char = "⚙️"
            alignment = Qt.AlignLeft
        elif is_assistant:
            icon_char = "A"
            alignment = Qt.AlignLeft
        else:
            icon_char = "A"
            alignment = Qt.AlignLeft

        return is_user, icon_char, alignment

    def _resolve_agent_metadata(self, sender: str, message_metadata: Optional[Dict[str, Any]] = None):
        if not self._crew_member_metadata:
            self._load_crew_member_metadata()

        agent_color = "#4a90e2"
        agent_icon = "🤖"
        crew_member_data: Dict[str, Any] = {}

        normalized_sender = sender.lower()
        sender_crew_member = self._crew_member_metadata.get(normalized_sender)
        if sender_crew_member:
            agent_color = sender_crew_member.config.color
            agent_icon = sender_crew_member.config.icon
            crew_member_data = {
                "name": sender_crew_member.config.name,
                "description": sender_crew_member.config.description,
                "color": sender_crew_member.config.color,
                "icon": sender_crew_member.config.icon,
                "soul": sender_crew_member.config.soul,
                "skills": sender_crew_member.config.skills,
                "model": sender_crew_member.config.model,
                "temperature": sender_crew_member.config.temperature,
                "max_steps": sender_crew_member.config.max_steps,
                "config_path": sender_crew_member.config.config_path,
                "crew_title": sender_crew_member.config.metadata.get("crew_title", normalized_sender),
            }
        else:
            if message_metadata:
                agent_color = message_metadata.get("color", agent_color)
                agent_icon = message_metadata.get("icon", agent_icon)
                crew_member_data = dict(message_metadata)
        return agent_color, agent_icon, crew_member_data

    # ─── Widget creation and sizing ──────────────────────────────────

    def _create_message_widget(self, item: ChatListItem, parent=None) -> QWidget:
        from app.ui.chat.card import AgentMessageCard, UserMessageCard

        if item.is_user:
            widget = UserMessageCard(item.user_content, parent)
        else:
            widget = AgentMessageCard(
                agent_message=item.agent_message,
                agent_color=item.agent_color,
                agent_icon=item.agent_icon,
                crew_member_metadata=item.crew_member_metadata,
                parent=parent,
            )
            widget.reference_clicked.connect(self.reference_clicked.emit)
        return widget

    # Minimum width to use for size hint calculation
    # This prevents incorrect size calculation when viewport is very small
    MIN_SIZING_WIDTH = 400

    def _build_sizing_widget(self, item: ChatListItem, width: int) -> QWidget:
        widget = self._create_message_widget(item, None)
        widget.setAttribute(Qt.WA_DontShowOnScreen, True)
        # Use a reasonable minimum width to avoid exaggerated height calculations
        actual_width = max(self.MIN_SIZING_WIDTH, width)
        widget.setFixedWidth(actual_width)
        if widget.layout():
            widget.layout().activate()
            widget.layout().update()
        # Force geometry update
        widget.setGeometry(0, 0, actual_width, 100)
        widget.adjustSize()
        # Ensure the size reflects the fixed width
        size = widget.size()
        if size.width() != actual_width:
            # If width didn't take, manually set it
            from PySide6.QtCore import QSize
            widget.resize(QSize(actual_width, size.height()))
        return widget

    def get_item_size_hint(self, option, index) -> QSize:
        item = index.data(self._model.ITEM_ROLE)
        if not item:
            return QSize(0, 0)

        width = option.rect.width()
        if width <= 0:
            width = self.list_view.viewport().width()

        # Use minimum width for calculation to avoid exaggerated heights
        calc_width = max(self.MIN_SIZING_WIDTH, width)

        cached = self._size_hint_cache.get(item.message_id, {}).get(calc_width)
        if cached:
            # If cached size was calculated with different width, adjust width
            result = QSize(cached)
            result.setWidth(width)
            return result

        widget = self._build_sizing_widget(item, calc_width)
        # Use size() instead of sizeHint() since we set a fixed width
        size = widget.size()
        widget.deleteLater()

        # Always return the actual display width, not the calculation width
        if size.width() <= 0:
            size.setWidth(max(1, width))
        else:
            size.setWidth(max(1, width))
        if size.height() < 1:
            size.setHeight(1)

        # Cache with the calculation width
        self._size_hint_cache.setdefault(item.message_id, {})[calc_width] = size
        return size

    def _invalidate_size_hint(self, message_id: str):
        """Invalidate size hint cache for a specific message."""
        if message_id in self._size_hint_cache:
            self._size_hint_cache.pop(message_id, None)
        # Also mark positions cache as dirty since heights may change
        self._invalidate_positions_cache()

    # ─── Viewport and scroll handling ────────────────────────────────

    def _schedule_visible_refresh(self):
        if not self._visible_refresh_timer.isActive():
            self._visible_refresh_timer.start(self.VISIBLE_REFRESH_DELAY_MS)

    def _on_viewport_resized(self):
        """Handle viewport resize with optimized cache handling."""
        # Only clear size hint cache if width changed significantly
        new_width = self.list_view.viewport().width()
        old_width_hint = next(iter(self._size_hint_cache.values()), {}).get(0, QSize(0, 0)).width() if self._size_hint_cache else 0

        if abs(new_width - old_width_hint) > 50:  # Significant width change
            # Clear widgets and cache only on significant width change
            self._size_hint_cache.clear()
            self._clear_visible_widgets()
            self.list_view.doItemsLayout()
            # Mark positions cache as dirty
            self._invalidate_positions_cache()

        self._schedule_visible_refresh()

    def _clear_visible_widgets(self):
        for row, widget in list(self._visible_widgets.items()):
            index = self._model.index(row, 0)
            self.list_view.setIndexWidget(index, None)
            widget.setParent(None)
            widget.deleteLater()
        self._visible_widgets = {}

    def _refresh_visible_widgets(self):
        """Refresh visible widgets with performance optimizations.

        Limits the number of widgets created per refresh to avoid blocking.
        """
        row_count = self._model.rowCount()

        if row_count <= 0:
            self._clear_visible_widgets()
            return

        first_row, last_row = self._get_visible_row_range()
        if first_row is None or last_row is None:
            return

        # Use larger buffer when at bottom to ensure more widgets are created
        # This helps when viewport is small (e.g., during initialization)
        scrollbar = self.list_view.verticalScrollBar()
        is_at_bottom = (scrollbar.value() >= scrollbar.maximum() - 10)

        if is_at_bottom:
            # At bottom, create widgets for more items above
            buffer_size = min(20, row_count)  # Show up to 20 items when at bottom
            # Also include items below if any (shouldn't happen at bottom)
            start_row = max(0, first_row - buffer_size)
            end_row = row_count - 1  # Always include all items to the end when at bottom
        else:
            buffer_size = 2
            start_row = max(0, first_row - buffer_size)
            end_row = min(row_count - 1, last_row + buffer_size)

        desired_rows = set(range(start_row, end_row + 1))

        # Limit number of widgets to create per refresh
        max_to_create = self.MAX_VISIBLE_WIDGETS
        widgets_to_create = [r for r in desired_rows if r not in self._visible_widgets]
        if len(widgets_to_create) > max_to_create:
            # Prioritize rows closer to the visible center
            visible_center = (first_row + last_row) // 2
            widgets_to_create.sort(key=lambda r: abs(r - visible_center))
            widgets_to_create = widgets_to_create[:max_to_create]
            desired_rows = set(widgets_to_create) | set(self._visible_widgets.keys())

        # Remove widgets that are no longer in the desired range
        for row in list(self._visible_widgets.keys()):
            if row not in desired_rows:
                index = self._model.index(row, 0)
                widget = self._visible_widgets.pop(row)
                self.list_view.setIndexWidget(index, None)
                widget.setParent(None)
                widget.deleteLater()

        # Create widgets for rows that need them
        for row in widgets_to_create:
            if row in self._visible_widgets:
                continue
            item = self._model.get_item(row)
            if not item:
                continue
            index = self._model.index(row, 0)
            widget = self._create_message_widget(item, self.list_view.viewport())
            # Set fixed width to match viewport width
            widget_width = self.list_view.viewport().width()
            widget.setFixedWidth(max(1, widget_width))
            # Get cached size or build sizing widget to determine height
            cached_size = self._size_hint_cache.get(item.message_id, {}).get(widget_width)
            if cached_size:
                item_height = cached_size.height()
            else:
                option = QStyleOptionViewItem()
                option.rect = self.list_view.viewport().rect()
                item_height = self.get_item_size_hint(option, index).height()
            widget.setFixedHeight(max(1, item_height))
            widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            if widget.layout():
                widget.layout().activate()
            self.list_view.setIndexWidget(index, widget)
            self._visible_widgets[row] = widget

    def _get_visible_row_range(self) -> Tuple[Optional[int], Optional[int]]:
        """Get the range of currently visible rows using cached positions.

        Uses binary search on cached row positions for O(log n) performance.
        """
        viewport = self.list_view.viewport()
        if viewport is None:
            return None, None

        # Rebuild cache if dirty
        if self._positions_cache_dirty:
            self._rebuild_positions_cache()

        scrollbar = self.list_view.verticalScrollBar()
        scroll_value = scrollbar.value()
        viewport_height = viewport.height()

        if viewport_height <= 0:
            viewport_height = 10  # Default fallback

        row_count = self._model.rowCount()

        if row_count == 0:
            return 0, 0

        # Binary search for first visible row
        scroll_bottom = scroll_value + viewport_height

        first_row = 0
        last_row = row_count - 1

        # Find first row where y + height > scroll_value
        low, high = 0, row_count - 1
        while low <= high:
            mid = (low + high) // 2
            if mid in self._row_positions_cache:
                y, h = self._row_positions_cache[mid]
                if y + h <= scroll_value:
                    low = mid + 1
                elif y > scroll_value:
                    high = mid - 1
                else:
                    first_row = mid
                    break
            else:
                # Cache miss, fall back to linear search for this section
                first_row = self._find_first_visible_linear(scroll_value, row_count)
                break

        # Find last row
        low, high = first_row, row_count - 1
        while low <= high:
            mid = (low + high) // 2
            if mid in self._row_positions_cache:
                y, h = self._row_positions_cache[mid]
                if y < scroll_bottom:
                    low = mid + 1
                elif y >= scroll_bottom:
                    high = mid - 1
                else:
                    last_row = mid
                    break
            else:
                # Cache miss, fall back to linear search
                last_row = self._find_last_visible_linear(first_row, scroll_bottom, row_count)
                break

        return first_row, last_row

    def _find_first_visible_linear(self, scroll_value: int, row_count: int) -> int:
        """Linear search fallback for first visible row."""
        for row in range(row_count):
            if row in self._row_positions_cache:
                y, h = self._row_positions_cache[row]
                if y + h > scroll_value:
                    return row
        return 0

    def _find_last_visible_linear(self, start_row: int, scroll_bottom: int, row_count: int) -> int:
        """Linear search fallback for last visible row."""
        for row in range(start_row, row_count):
            if row in self._row_positions_cache:
                y, _ = self._row_positions_cache[row]
                if y >= scroll_bottom:
                    return row - 1
        return row_count - 1

    def _on_model_data_changed(self, top_left: QModelIndex, bottom_right: QModelIndex, roles=None):
        for row in range(top_left.row(), bottom_right.row() + 1):
            self._update_widget_for_row(row)
        self._schedule_visible_refresh()

    def _update_widget_for_row(self, row: int):
        widget = self._visible_widgets.get(row)
        if not widget:
            return
        item = self._model.get_item(row)
        if not item:
            return
        if item.is_user:
            if hasattr(widget, "set_content"):
                widget.set_content(item.user_content)
        else:
            if hasattr(widget, "update_from_agent_message") and item.agent_message:
                widget.update_from_agent_message(item.agent_message)

        # Update widget height after content change
        self._invalidate_size_hint(item.message_id)
        option = QStyleOptionViewItem()
        option.rect = self.list_view.viewport().rect()
        index = self._model.index(row, 0)
        new_size = self.get_item_size_hint(option, index)
        widget.setFixedHeight(max(1, new_size.height()))

    def _on_rows_inserted(self, parent: QModelIndex, start: int, end: int):
        # Mark positions cache as dirty and refresh
        self._invalidate_positions_cache()
        self._schedule_visible_refresh()
        if self._user_at_bottom:
            self._schedule_scroll()

    def _on_scroll_value_changed(self, value: int):
        """Handle scroll value changes with throttling."""
        # Store pending scroll value for throttled processing
        self._pending_scroll_value = value

        # Start throttle timer
        self._scroll_throttle_timer.start(self.SCROLL_THROTTLE_MS)

        # Immediately trigger refresh if significant scroll
        scrollbar = self.list_view.verticalScrollBar()
        scroll_diff = abs(value - self._scroll_delta_since_last_refresh)

        if scroll_diff > 100:  # Significant scroll threshold
            self._scroll_delta_since_last_refresh = value
            self._schedule_visible_refresh()

    def _on_scroll_throttled(self):
        """Handle throttled scroll event - debounced processing."""
        if self._pending_scroll_value is None:
            return

        value = self._pending_scroll_value
        self._pending_scroll_value = None

        scrollbar = self.list_view.verticalScrollBar()
        scroll_diff = scrollbar.maximum() - value
        was_at_bottom = self._user_at_bottom
        self._user_at_bottom = scroll_diff < self.SCROLL_BOTTOM_THRESHOLD

        # Detect scroll to top - trigger loading older messages
        if value < self.SCROLL_TOP_THRESHOLD and self._load_state.has_more_older and not self._loading_older:
            self._load_older_messages()

        if self._user_at_bottom and not was_at_bottom:
            if not self._bottom_reached:
                self._bottom_reached = True
                self.load_more_requested.emit()
        elif not self._user_at_bottom:
            self._bottom_reached = False

        # Schedule refresh after throttled scroll processing
        self._schedule_visible_refresh()

    def _scroll_to_bottom(self):
        if self._user_at_bottom:
            self.list_view.scrollToBottom()

    def _schedule_scroll(self):
        self._scroll_timer.start(50)

    def _ensure_widgets_visible_and_scrolled(self):
        """Ensure widgets are created and scrolled to bottom after initial load.

        This method is called after a delay to ensure that:
        1. The viewport has its final size
        2. Widgets are created for visible items
        3. The view is scrolled to the bottom
        """
        try:
            # Force refresh of visible widgets
            self._refresh_visible_widgets()

            # Ensure we're scrolled to bottom
            self._user_at_bottom = True
            self.list_view.scrollToBottom()

            # One more refresh after scrolling to ensure widgets in the new
            # visible range are created
            QTimer.singleShot(50, self._refresh_visible_widgets)

        except Exception as e:
            logger.error(f"Error in _ensure_widgets_visible_and_scrolled: {e}")

    # ─── Public API for direct message manipulation ───────────────────

    def _add_historical_message(self, sender: str, message):
        if not message.content:
            return None

        from agent.chat.agent_chat_message import AgentMessage as ChatAgentMessage
        from agent.chat.agent_chat_types import MessageType
        from agent.chat.content import TextContent

        is_user = message.role == "user"
        is_user_normalized = sender.lower() in [tr("用户").lower(), "用户", "user", tr("user").lower()]

        if is_user or is_user_normalized:
            return self.add_user_message(message.content)

        message_id = (
            message.metadata.get("message_id", f"hist_{message.timestamp}")
            if message.metadata else f"hist_{message.timestamp}"
        )

        agent_message = ChatAgentMessage(
            message_type=MessageType.TEXT,
            sender_id=sender,
            sender_name=sender,
            message_id=message_id,
            structured_content=[TextContent(text=message.content)] if message.content else [],
        )

        agent_color, agent_icon, crew_member_data = self._resolve_agent_metadata(sender, message.metadata)

        item = ChatListItem(
            message_id=message_id,
            sender_id=sender,
            sender_name=sender,
            is_user=False,
            agent_message=agent_message,
            agent_color=agent_color,
            agent_icon=agent_icon,
            crew_member_metadata=crew_member_data,
        )
        self._model.add_item(item)
        self._schedule_scroll()
        return item

    def append_message(self, sender: str, message: str, message_id: str = None):
        if not message:
            return None

        from agent.chat.agent_chat_message import AgentMessage as ChatAgentMessage
        from agent.chat.agent_chat_types import MessageType
        from agent.chat.content import TextContent

        is_user, _icon_char, _alignment = self._get_sender_info(sender)
        if is_user:
            return self.add_user_message(message)

        if not message_id:
            message_id = str(uuid.uuid4())

        agent_message = ChatAgentMessage(
            message_type=MessageType.TEXT,
            sender_id=sender,
            sender_name=sender,
            message_id=message_id,
            structured_content=[TextContent(text=message)] if message else [],
        )

        agent_color, agent_icon, crew_member_data = self._resolve_agent_metadata(sender)

        item = ChatListItem(
            message_id=message_id,
            sender_id=sender,
            sender_name=sender,
            is_user=False,
            agent_message=agent_message,
            agent_color=agent_color,
            agent_icon=agent_icon,
            crew_member_metadata=crew_member_data,
        )

        row = self._model.add_item(item)
        self._schedule_scroll()
        return self._visible_widgets.get(row)

    def update_last_message(self, message: str):
        row_count = self._model.rowCount()
        if row_count <= 0:
            return

        last_row = row_count - 1
        item = self._model.get_item(last_row)
        if not item:
            return

        if item.is_user:
            item.user_content = message
            self._invalidate_size_hint(item.message_id)
            self._model.notify_row_changed(last_row)
        else:
            self.update_agent_card(item.message_id, content=message, append=False)

        self._schedule_scroll()

    def start_streaming_message(self, sender: str) -> str:
        message_id = str(uuid.uuid4())
        self.append_message(sender, "...", message_id)
        return message_id

    def update_streaming_message(self, message_id: str, content: str):
        item = self._model.get_item_by_message_id(message_id)
        if not item:
            return
        if item.is_user:
            item.user_content = content
            self._invalidate_size_hint(item.message_id)
            row = self._model.get_row_by_message_id(message_id)
            if row is not None:
                self._model.notify_row_changed(row)
        else:
            self.update_agent_card(message_id, content=content, append=False)
        self._schedule_scroll()

    def add_user_message(self, content: str):
        message_id = str(uuid.uuid4())
        item = ChatListItem(
            message_id=message_id,
            sender_id="user",
            sender_name=tr("User"),
            is_user=True,
            user_content=content,
        )
        row = self._model.add_item(item)
        self._schedule_scroll()
        return self._visible_widgets.get(row)

    def get_or_create_agent_card(self, message_id: str, agent_name: str, title=None):
        existing_row = self._model.get_row_by_message_id(message_id)
        if existing_row is not None:
            return self._visible_widgets.get(existing_row)

        from agent.chat.agent_chat_message import AgentMessage as ChatAgentMessage
        from agent.chat.agent_chat_types import MessageType

        agent_message = ChatAgentMessage(
            message_type=MessageType.TEXT,
            sender_id=agent_name,
            sender_name=agent_name,
            message_id=message_id,
            structured_content=[],
        )

        agent_color, agent_icon, crew_member_data = self._resolve_agent_metadata(agent_name)

        item = ChatListItem(
            message_id=message_id,
            sender_id=agent_name,
            sender_name=agent_name,
            is_user=False,
            agent_message=agent_message,
            agent_color=agent_color,
            agent_icon=agent_icon,
            crew_member_metadata=crew_member_data,
        )

        row = self._model.add_item(item)
        self._agent_current_cards[agent_name] = message_id
        self._schedule_scroll()
        return self._visible_widgets.get(row)

    def get_agent_current_card(self, agent_name: str):
        message_id = self._agent_current_cards.get(agent_name)
        if message_id:
            row = self._model.get_row_by_message_id(message_id)
            if row is not None:
                return self._visible_widgets.get(row)
        return None

    def update_agent_card(
        self,
        message_id: str,
        content: str = None,
        append: bool = True,
        is_thinking: bool = False,
        thinking_text: str = "",
        is_complete: bool = False,
        structured_content=None,
        error: str = None,
    ):
        item = self._model.get_item_by_message_id(message_id)
        if not item or not item.agent_message:
            return

        card = None
        row = self._model.get_row_by_message_id(message_id)
        if row is not None:
            card = self._visible_widgets.get(row)

        from agent.chat.content import TextContent, TypingContent, TypingState
        from agent.chat.agent_chat_types import ContentType
        from agent.chat.content import StructureContent

        agent_message = item.agent_message

        if content is not None:
            text_content = None
            for sc in agent_message.structured_content:
                if sc.content_type == ContentType.TEXT:
                    text_content = sc
                    break
            if text_content:
                text_content.text = (text_content.text or "") + content if append else content
            else:
                agent_message.structured_content.append(TextContent(text=content))

            if card:
                final_content = text_content.text if text_content else content
                card.set_content(final_content)
                if card.has_typing_indicator():
                    card.remove_typing_indicator()

        if structured_content is not None:
            items = (
                [structured_content]
                if isinstance(structured_content, StructureContent)
                else list(structured_content)
            )
            for sc in items:
                is_typing_content = isinstance(sc, TypingContent) or sc.content_type == ContentType.TYPING
                is_typing_end = (
                    is_typing_content
                    and isinstance(sc, TypingContent)
                    and sc.state == TypingState.END
                )

                if is_typing_end:
                    agent_message.structured_content = [
                        existing for existing in agent_message.structured_content
                        if existing.content_type != ContentType.TYPING
                    ]
                    if card and card.has_typing_indicator():
                        card.remove_typing_indicator()
                    continue

                agent_message.structured_content.append(sc)
                if card:
                    card.add_structure_content_widget(sc)
                    if not is_typing_content and is_complete:
                        if card.has_typing_indicator():
                            card.remove_typing_indicator()

        if error:
            error_text = f"❌ Error: {error}"
            agent_message.structured_content = [
                sc for sc in agent_message.structured_content
                if sc.content_type != ContentType.TEXT
                and sc.content_type != ContentType.TYPING
            ]
            agent_message.structured_content.append(TextContent(text=error_text))
            if card:
                card.set_content(error_text)
                if card.has_typing_indicator():
                    card.remove_typing_indicator()

        if is_complete:
            agent_message.structured_content = [
                sc for sc in agent_message.structured_content
                if sc.content_type != ContentType.TYPING
            ]

        self._invalidate_size_hint(message_id)
        if row is not None:
            self._model.notify_row_changed(row)
        self._schedule_scroll()

    async def handle_agent_message(self, message: AgentMessage):
        if message.sender_id == "user":
            return

        if getattr(message, "message_type", None):
            from agent.chat.agent_chat_types import MessageType
            if message.message_type == MessageType.SYSTEM and message.metadata.get("event_type") in (
                "crew_member_start", "producer_start", "mentioned_agent_start",
                "responding_agent_start", "plan_update", "plan_created",
            ):
                return

        message_id = (
            getattr(message, "message_id", None)
            or (message.metadata.get("message_id") if message.metadata else None)
        )
        if not message_id:
            message_id = str(uuid.uuid4())

        self.get_or_create_agent_card(
            message_id,
            message.sender_name,
            message.sender_name,
        )

        has_structure = bool(message.structured_content)
        if has_structure:
            for sc in message.structured_content:
                self.update_agent_card(message_id, structured_content=sc)

    @Slot(object, object)
    def handle_stream_event(self, event, session):
        if event.event_type == "error":
            error_content = event.data.get("content", "Unknown error occurred")
            message_id = str(uuid.uuid4())
            self.get_or_create_agent_card(message_id, "System", "System")
            from agent.chat.content import ErrorContent
            error_structure = ErrorContent(error_message=error_content)
            self.update_agent_card(
                message_id,
                structured_content=error_structure,
                error=error_content,
            )
        elif event.event_type == "agent_response":
            content = event.data.get("content", "")
            sender_name = event.data.get("sender_name", "Unknown")
            sender_id = event.data.get("sender_id", sender_name.lower())
            session_id = event.data.get("session_id", "unknown")

            if sender_id == "user":
                return

            message_id = event.data.get("message_id")
            if not message_id:
                message_id = f"response_{session_id}_{uuid.uuid4()}"

            self.get_or_create_agent_card(message_id, sender_name, sender_name)
            from agent.chat.content import TextContent
            text_structure = TextContent(text=content)
            self.update_agent_card(message_id, structured_content=text_structure)
        elif event.event_type in ["skill_start", "skill_progress", "skill_end"]:
            skill_name = event.data.get("skill_name", "Unknown")
            sender_name = event.data.get("sender_name", "Unknown")
            sender_id = event.data.get("sender_id", sender_name.lower())
            message_id = event.data.get("message_id", str(uuid.uuid4()))

            if sender_id == "user":
                return

            if event.event_type == "skill_start":
                content = f"[Skill: {skill_name}] Starting execution..."
            elif event.event_type == "skill_progress":
                message = event.data.get("progress_text", "Processing...")
                content = f"[Skill: {skill_name}] {message}"
            elif event.event_type == "skill_end":
                result = event.data.get("result", "No result returned")
                content = f"[Skill: {skill_name}] Completed. Result: {result}"
            else:
                content = f"[Skill: {skill_name}] Unknown skill status"

            self.get_or_create_agent_card(message_id, sender_name, sender_name)
            from agent.chat.content import ProgressContent
            skill_content = ProgressContent(
                progress=content,
                percentage=None,
                tool_name=skill_name,
            )
            self.update_agent_card(
                message_id,
                content=content,
                append=False,
                structured_content=skill_content,
            )
        elif hasattr(event, "content") and event.content:
            sender_id = getattr(event, "sender_id", "")
            if hasattr(event, "agent_name"):
                sender_id = getattr(event, "agent_name", "").lower()

            if sender_id == "user":
                return

            message_type = getattr(event, "message_type", None)
            from agent.chat.agent_chat_types import MessageType
            card = self._model.get_item_by_message_id(event.message_id)
            if not card:
                agent_name = getattr(event, "agent_name", "Unknown")
                self.get_or_create_agent_card(
                    event.message_id,
                    agent_name,
                    getattr(event, "title", None),
                )

            if message_type == MessageType.THINKING:
                from agent.chat.content import ThinkingContent
                if isinstance(event.content, ThinkingContent):
                    thinking_structure = event.content
                else:
                    thinking_content = event.content
                    if thinking_content.startswith("🤔 Thinking: "):
                        thinking_content = thinking_content[len("🤔 Thinking: "):]
                    thinking_structure = ThinkingContent(
                        thought=thinking_content,
                        title="Thinking Process",
                        description="Agent's thought process",
                    )
                self.update_agent_card(event.message_id, structured_content=thinking_structure)
            else:
                from agent.chat.content import TextContent
                text_structure = TextContent(text=event.content)
                self.update_agent_card(event.message_id, structured_content=text_structure)

    def sync_from_session(self, session):
        pass

    def clear(self):
        self._stop_new_data_check_timer()
        self._clear_visible_widgets()
        self._size_hint_cache.clear()
        self._agent_current_cards.clear()
        self._model.clear()
        # Reset load state
        self._load_state = LoadState()
        self._loading_older = False

    def __del__(self):
        """Destructor."""
