"""Main widget for agent chat list with virtualized rendering.

This module provides the main widget that orchestrates the chat list,
including data loading, widget management, and event handling.
"""

import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple, TYPE_CHECKING

from PySide6.QtCore import Qt, Signal, Slot, QTimer, QModelIndex, QSize
from PySide6.QtWidgets import (
    QVBoxLayout, QWidget, QAbstractItemView,
    QStyleOptionViewItem, QSizePolicy
)
from PySide6.QtGui import QResizeEvent

from agent import AgentMessage
from app.ui.base_widget import BaseWidget
from utils.i18n_utils import tr
from agent.chat.history.agent_chat_history_service import FastMessageHistoryService, message_saved
from agent.chat.history.agent_chat_storage import MessageLogHistory

# Late imports for agent chat components (avoid circular imports)
from agent.chat.agent_chat_message import AgentMessage as ChatAgentMessage
from agent.chat.agent_chat_types import MessageType, ContentType
from agent.chat.content import (
    TextContent, StructureContent, ThinkingContent, TypingContent,
    TypingState, ProgressContent, ErrorContent
)

# Import local modules
from app.ui.chat.list.agent_chat_list_items import (
    ChatListItem, MessageGroup, LoadState
)
from app.ui.chat.list.agent_chat_list_model import AgentChatListModel
from app.ui.chat.list.agent_chat_list_delegate import AgentChatListDelegate
from app.ui.chat.list.agent_chat_list_view import AgentChatListView

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.data.workspace import Workspace

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
    VISIBLE_REFRESH_DELAY_MS = 8  # ~60fps
    SCROLL_THROTTLE_MS = 50  # Throttle scroll events
    MAX_VISIBLE_WIDGETS = 30  # Limit widgets created at once
    MAX_TOTAL_WIDGETS = 300  # Maximum total widgets to keep (soft limit)

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

        # Track if user is actively dragging the scrollbar
        self._is_dragging_scrollbar = False

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
        self._is_prepending = False  # Flag to track prepend operations

        # Cache history instance for reduced overhead
        self._history: Optional[MessageLogHistory] = None

        # Connect to message_saved signal for storage-driven refresh
        self._connect_to_storage_signals()

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
        self._is_prepending = False  # Reset prepend flag
        # Invalidate history cache
        self._history = None
        # Clear position cache
        self._positions_cache_dirty = True
        self._row_positions_cache.clear()
        # Reset scroll tracking
        self._scroll_delta_since_last_refresh = 0
        self._pending_scroll_value = None
        # Clear visible widgets and size hint cache
        self._clear_visible_widgets()
        self._size_hint_cache.clear()
        # Reconnect to storage signals for new project
        self._connect_to_storage_signals()
        self._load_recent_conversation()

    def refresh_crew_member_metadata(self):
        self._load_crew_member_metadata()

    def _connect_to_storage_signals(self):
        """Connect to storage signals for storage-driven refresh."""
        try:
            message_saved.connect(self._on_message_saved, weak=False)
            logger.debug("Connected to message_saved signal")
        except Exception as e:
            logger.error(f"Error connecting to message_saved signal: {e}")

    def _disconnect_from_storage_signals(self):
        """Disconnect from storage signals."""
        try:
            message_saved.disconnect(self._on_message_saved)
            logger.debug("Disconnected from message_saved signal")
        except Exception:
            pass  # Signal might not be connected

    def _on_message_saved(self, sender, workspace_path: str, project_name: str, message_id: str):
        """Handle message_saved signal from storage.

        This is called after a message is successfully written to storage.
        We trigger a data refresh to load the new message from storage.
        """
        # Only refresh if this message belongs to our current project
        if (workspace_path == self.workspace.workspace_path and
            project_name == self.workspace.project_name):
            # Trigger immediate data refresh from storage
            self._check_for_new_data()

    def _invalidate_positions_cache(self):
        """Mark the positions cache as dirty - needs rebuild."""
        self._positions_cache_dirty = True

    def _rebuild_positions_cache(self, force: bool = False):
        """Rebuild the row positions cache from scratch.

        Args:
            force: If True, rebuild even if cache is not marked dirty
        """
        if not force and not self._positions_cache_dirty:
            return

        self._row_positions_cache.clear()
        current_y = 0
        row_count = self._model.rowCount()

        try:
            # Reuse option object for better performance
            option = QStyleOptionViewItem()
            option.rect = self.list_view.viewport().rect()

            # CRITICAL: Ensure viewport has valid dimensions before building cache
            viewport_width = option.rect.width()
            if viewport_width <= 0:
                logger.debug(
                    f"_rebuild_positions_cache: Invalid viewport width ({viewport_width}), "
                    f"forcing layout update"
                )
                # Force layout to get proper viewport dimensions
                self.list_view.doItemsLayout()
                option.rect = self.list_view.viewport().rect()
                viewport_width = option.rect.width()
                if viewport_width <= 0:
                    # Still invalid? Use a reasonable default
                    logger.warning(
                        f"_rebuild_positions_cache: Viewport width still {viewport_width}, "
                        f"using default width"
                    )
                    option.rect = QRect(0, 0, self.MIN_SIZING_WIDTH, self.list_view.viewport().height())

            for row in range(row_count):
                index = self._model.index(row, 0)
                size = self.get_item_size_hint(option, index)

                self._row_positions_cache[row] = (current_y, size.height())
                current_y += size.height()

            self._total_height_cache = current_y
            self._positions_cache_dirty = False

            # Sync positions to list view for smooth scrolling
            # Don't restore scroll position if we're in the middle of a prepend operation
            # (scroll restoration will be handled by _restore_scroll_after_prepend)
            restore_scroll = not self._is_prepending
            self.list_view.set_row_positions(
                self._row_positions_cache,
                self._total_height_cache,
                restore_scroll=restore_scroll
            )

        except Exception as e:
            logger.error(f"Error rebuilding positions cache: {e}", exc_info=True)
            self._positions_cache_dirty = True  # Mark dirty so we try again

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

    def _clear_all_caches_and_model(self):
        """Clear all caches and the model for a fresh start."""
        self._model.clear()
        self._size_hint_cache.clear()
        self._clear_visible_widgets()
        self._load_state.known_message_ids.clear()
        self._load_state.unique_message_count = 0
        self._load_state.has_more_older = False

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
                self._clear_all_caches_and_model()

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
                self._clear_all_caches_and_model()
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

                # Set flag to prevent automatic scroll restoration during cache rebuild
                self._is_prepending = True

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
        try:
            new_max = scrollbar.maximum()
            delta = new_max - old_max
            scrollbar.setValue(old_value + delta)
            self._schedule_visible_refresh()
        finally:
            # Clear the prepend flag after scroll restoration is complete
            self._is_prepending = False

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

    def _schedule_visible_refresh(self, immediate: bool = False):
        """Schedule a refresh of visible widgets.

        Args:
            immediate: If True, refresh immediately without delay (useful during scrolling)
        """
        if immediate:
            # Cancel any pending refresh and do it now
            self._visible_refresh_timer.stop()
            self._refresh_visible_widgets()
        else:
            if not self._visible_refresh_timer.isActive():
                # Use shorter delay for more responsive scrolling
                self._visible_refresh_timer.start(8)  # Reduced from 16ms to 8ms

    def _on_viewport_resized(self):
        """Handle viewport resize with optimized cache handling."""
        # Track previous viewport width for comparison
        new_width = self.list_view.viewport().width()
        old_width = getattr(self, '_prev_viewport_width', 0)

        if old_width > 0 and abs(new_width - old_width) > 50:
            # Significant width change - clear caches
            self._size_hint_cache.clear()
            self._clear_visible_widgets()
            self.list_view.doItemsLayout()
            self._invalidate_positions_cache()

        self._prev_viewport_width = new_width
        self._schedule_visible_refresh()

    def _clear_visible_widgets(self):
        """Clear all visible widgets and clean up resources."""
        for row, widget in list(self._visible_widgets.items()):
            index = self._model.index(row, 0)
            self.list_view.setIndexWidget(index, None)
            # setIndexWidget already handles parent removal, just deleteLater
            widget.deleteLater()
        self._visible_widgets = {}

    def _refresh_visible_widgets(self):
        """Refresh visible widgets with performance optimizations.

        Uses a 'don't destroy' approach - once created, widgets are kept around
        to prevent black screens during scrolling. Only creates new widgets as needed.

        CRITICAL: Rebuild cache BEFORE creating widgets to ensure consistent sizing.
        """
        row_count = self._model.rowCount()

        if row_count <= 0:
            self._clear_visible_widgets()
            return

        first_row, last_row = self._get_visible_row_range()
        if first_row is None or last_row is None:
            logger.debug(
                f"_refresh_visible_widgets: Invalid range (first_row={first_row}, "
                f"last_row={last_row}, row_count={row_count}, "
                f"cache_size={len(self._row_positions_cache)}, "
                f"cache_dirty={self._positions_cache_dirty})"
            )
            return

        # CRITICAL: Rebuild cache FIRST, before creating widgets
        # This ensures all size calculations use consistent viewport dimensions
        if self._positions_cache_dirty:
            self._rebuild_positions_cache()

        # Use larger buffer when at bottom to ensure more widgets are created
        scrollbar = self.list_view.verticalScrollBar()
        is_at_bottom = (scrollbar.value() >= scrollbar.maximum() - 10)

        # Detect if we're actively scrolling
        is_scrolling = (abs(scrollbar.value() - self._scroll_delta_since_last_refresh) > 20)

        if is_at_bottom:
            # At bottom, create widgets for more items above
            buffer_size = min(20, row_count)
            start_row = max(0, first_row - buffer_size)
            end_row = row_count - 1
        elif is_scrolling:
            # During scrolling, use larger buffer to prevent blank areas
            buffer_size = 10
            start_row = max(0, first_row - buffer_size)
            end_row = min(row_count - 1, last_row + buffer_size)
        else:
            buffer_size = 5
            start_row = max(0, first_row - buffer_size)
            end_row = min(row_count - 1, last_row + buffer_size)

        desired_rows = set(range(start_row, end_row + 1))

        # Only create widgets that don't exist yet - NEVER delete existing widgets
        widgets_to_create = [r for r in desired_rows if r not in self._visible_widgets]

        # Limit number of widgets to create per refresh to avoid blocking
        max_to_create = self.MAX_VISIBLE_WIDGETS * 2 if is_scrolling else self.MAX_VISIBLE_WIDGETS
        if len(widgets_to_create) > max_to_create:
            # Prioritize rows closer to the visible center
            visible_center = (first_row + last_row) // 2
            widgets_to_create.sort(key=lambda r: abs(r - visible_center))
            widgets_to_create = widgets_to_create[:max_to_create]

        # NOTE: We DON'T remove widgets that are no longer in desired range.
        # This "don't destroy" approach prevents black screens during scrolling.
        # Widgets are only cleared when explicitly needed (project switch, etc.)

        # Cache viewport dimensions and option for better performance
        widget_width = max(1, self.list_view.viewport().width())
        option = QStyleOptionViewItem()
        option.rect = self.list_view.viewport().rect()

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
            widget.setFixedWidth(widget_width)
            # Get cached size - cache was already rebuilt above, so should be available
            cached_size = self._size_hint_cache.get(item.message_id, {}).get(widget_width)
            if cached_size:
                item_height = cached_size.height()
            else:
                item_height = self.get_item_size_hint(option, index).height()
            widget.setFixedHeight(max(1, item_height))
            widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            if widget.layout():
                widget.layout().activate()
            self.list_view.setIndexWidget(index, widget)
            self._visible_widgets[row] = widget

        # Sync positions to list view for smooth scrolling (cache already rebuilt above)
        if self._row_positions_cache:
            self.list_view.set_row_positions(
                self._row_positions_cache,
                self._total_height_cache,
                restore_scroll=False  # Don't interfere with scrolling
            )

        # Optional: Clean up widgets if we exceed the soft limit
        # This prevents unlimited memory growth while still avoiding black screens
        current_widget_count = len(self._visible_widgets)
        if current_widget_count > self.MAX_TOTAL_WIDGETS:
            # Remove widgets farthest from the visible range
            # Keep widgets closest to visible range
            all_widget_rows = sorted(self._visible_widgets.keys())
            rows_to_keep = set()

            # Always keep widgets in visible range + buffer
            buffer = 20
            keep_start = max(0, first_row - buffer)
            keep_end = min(row_count - 1, last_row + buffer)
            for r in all_widget_rows:
                if keep_start <= r <= keep_end:
                    rows_to_keep.add(r)

            # Also keep some widgets on both sides (up to the limit)
            remaining_slots = self.MAX_TOTAL_WIDGETS - len(rows_to_keep)

            # Add closest widgets above visible range
            for r in reversed(all_widget_rows):
                if r < keep_start and remaining_slots > 0:
                    rows_to_keep.add(r)
                    remaining_slots -= 1

            # Add closest widgets below visible range
            for r in all_widget_rows:
                if r > keep_end and remaining_slots > 0:
                    rows_to_keep.add(r)
                    remaining_slots -= 1

            # Remove widgets not in keep set
            removed_count = 0
            for row in list(self._visible_widgets.keys()):
                if row not in rows_to_keep:
                    index = self._model.index(row, 0)
                    widget = self._visible_widgets.pop(row)
                    self.list_view.setIndexWidget(index, None)
                    widget.deleteLater()
                    removed_count += 1

            if removed_count > 0:
                logger.debug(
                    f"_refresh_visible_widgets: Cleaned up {removed_count} old widgets, "
                    f"kept {len(self._visible_widgets)} (limit: {self.MAX_TOTAL_WIDGETS})"
                )
        elif current_widget_count > 200:
            # Just log a warning
            logger.debug(
                f"_refresh_visible_widgets: High widget count ({current_widget_count}), "
                f"model rows: {row_count}, visible range: {first_row}-{last_row}"
            )

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

        # If cache is empty but we have rows, rebuild it
        if not self._row_positions_cache and row_count > 0:
            logger.debug(
                f"_get_visible_row_range: Cache empty, rebuilding (row_count={row_count})"
            )
            self._rebuild_positions_cache(force=True)
            # Still empty after rebuild? Something is wrong
            if not self._row_positions_cache:
                logger.warning(
                    f"_get_visible_row_range: Cache still empty after rebuild, "
                    f"returning default range (0, {row_count - 1})"
                )
                return 0, row_count - 1

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

        # Validate and clamp the returned range to ensure it's valid
        if first_row < 0:
            first_row = 0
        if first_row >= row_count:
            first_row = row_count - 1
        if last_row < first_row:
            last_row = first_row
        if last_row >= row_count:
            last_row = row_count - 1

        # Final sanity check - if still invalid, return safe defaults
        if first_row is None or last_row is None or first_row < 0 or last_row < 0:
            logger.warning(
                f"_get_visible_row_range: Invalid range after calculation, "
                f"using safe defaults (0, {max(0, row_count - 1)})"
            )
            return 0, max(0, row_count - 1)

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
        """Handle new rows inserted into the model.

        When new messages are added, we need to:
        1. Invalidate the positions cache (rows have shifted)
        2. Schedule refresh to create widgets for new rows
        3. Scroll to bottom if user was at bottom

        NOTE: We DON'T rebuild cache here because viewport may not be ready yet.
        Let _refresh_visible_widgets handle cache rebuild at the right time.
        """
        # Mark positions cache as dirty - rows have shifted
        self._invalidate_positions_cache()

        # Schedule refresh to create widgets for new rows
        # Don't rebuild cache here - let _refresh_visible_widgets do it
        # when viewport is properly initialized
        self._schedule_visible_refresh(immediate=True)

        # Scroll to bottom if user was at bottom (for smooth chat experience)
        if self._user_at_bottom:
            self._schedule_scroll()

    def _on_scroll_value_changed(self, value: int):
        """Handle scroll value changes with throttling."""
        # Store pending scroll value for throttled processing
        self._pending_scroll_value = value

        # Detect rapid scrolling (likely user dragging)
        scroll_diff = abs(value - self._scroll_delta_since_last_refresh)

        # During rapid scrolling, refresh more aggressively
        if scroll_diff > 50:  # Reduced from 100 for more responsive updates
            self._scroll_delta_since_last_refresh = value
            self._schedule_visible_refresh(immediate=True)  # Immediate refresh during scrolling
        else:
            # For small scrolls, use delayed refresh
            self._schedule_visible_refresh(immediate=False)

        # Start throttle timer for loading messages etc
        self._scroll_throttle_timer.start(self.SCROLL_THROTTLE_MS)

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
            # Ensure the widget has been properly laid out and has valid viewport size
            self.list_view.ensurePolished()

            # Force rebuild the position cache first
            if self._positions_cache_dirty or not self._row_positions_cache:
                self._rebuild_positions_cache(force=True)

            # Check viewport size
            viewport_height = self.list_view.viewport().height()
            if viewport_height <= 0:
                logger.warning(f"Viewport height is {viewport_height}, forcing layout update")
                self.list_view.doItemsLayout()
                viewport_height = self.list_view.viewport().height()
                logger.info(f"After layout, viewport height is {viewport_height}")

            # Force refresh of visible widgets
            self._refresh_visible_widgets()

            # Ensure we're scrolled to bottom
            self._user_at_bottom = True
            self.list_view.scrollToBottom()

            # One more refresh after scrolling to ensure widgets in the new
            # visible range are created
            QTimer.singleShot(50, self._refresh_visible_widgets)

            logger.debug(
                f"_ensure_widgets_visible_and_scrolled completed: "
                f"rows={self._model.rowCount()}, "
                f"widgets={len(self._visible_widgets)}, "
                f"viewport_height={viewport_height}"
            )

        except Exception as e:
            logger.error(f"Error in _ensure_widgets_visible_and_scrolled: {e}", exc_info=True)

    # ─── Public API for direct message manipulation ───────────────────

    def _add_historical_message(self, sender: str, message):
        if not message.content:
            return None

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

        is_user = self._get_sender_info(sender)[0]
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
            if message.message_type == MessageType.SYSTEM and message.metadata.get("event_type") in (
                "crew_member_start", "mentioned_agent_start",
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

    # ─── Stream event handling helper methods ─────────────────────────────

    def _handle_error_event(self, event) -> None:
        """Handle error type stream events."""
        error_content = event.data.get("content", "Unknown error occurred")
        message_id = str(uuid.uuid4())
        self.get_or_create_agent_card(message_id, "System", "System")
        error_structure = ErrorContent(error_message=error_content)
        self.update_agent_card(
            message_id,
            structured_content=error_structure,
            error=error_content,
        )

    def _handle_agent_response_event(self, event) -> None:
        """Handle agent_response type stream events."""
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
        text_structure = TextContent(text=content)
        self.update_agent_card(message_id, structured_content=text_structure)

    def _handle_skill_event(self, event) -> None:
        """Handle skill_start, skill_progress, skill_end type stream events."""
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

    def _handle_content_event(self, event) -> None:
        """Handle events with content attribute."""
        sender_id = getattr(event, "sender_id", "")
        if hasattr(event, "agent_name"):
            sender_id = getattr(event, "agent_name", "").lower()

        if sender_id == "user":
            return

        message_type = getattr(event, "message_type", None)
        card = self._model.get_item_by_message_id(event.message_id)
        if not card:
            agent_name = getattr(event, "agent_name", "Unknown")
            self.get_or_create_agent_card(
                event.message_id,
                agent_name,
                getattr(event, "title", None),
            )

        if message_type == MessageType.THINKING:
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
            text_structure = TextContent(text=event.content)
            self.update_agent_card(event.message_id, structured_content=text_structure)

    @Slot(object, object)
    def handle_stream_event(self, event, session):
        """Handle stream events by dispatching to appropriate handler."""
        if event.event_type == "error":
            self._handle_error_event(event)
        elif event.event_type == "agent_response":
            self._handle_agent_response_event(event)
        elif event.event_type in ["skill_start", "skill_progress", "skill_end"]:
            self._handle_skill_event(event)
        elif hasattr(event, "content") and event.content:
            self._handle_content_event(event)

    def sync_from_session(self, session):
        pass

    def clear(self):
        self._stop_new_data_check_timer()
        self._disconnect_from_storage_signals()
        self._clear_visible_widgets()
        self._size_hint_cache.clear()
        self._agent_current_cards.clear()
        self._model.clear()
        # Reset load state
        self._load_state = LoadState()
        self._loading_older = False

    def __del__(self):
        """Destructor."""
