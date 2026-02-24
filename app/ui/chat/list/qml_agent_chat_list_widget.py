"""QML-based AgentChatListWidget with Qt Quick Controls 2.

This module provides a complete rewrite of the agent chat list using QML + Qt Quick,
offering superior performance with dynamic heights, smooth scrolling, and 60 FPS rendering.
"""

import uuid
import logging
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot, QObject, QUrl, Property, QTimer
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QWidget, QVBoxLayout

from agent import AgentMessage
from agent.chat.agent_chat_message import AgentMessage as ChatAgentMessage
from agent.chat.agent_chat_types import ContentType
from agent.chat.content import TextContent, StructureContent
from agent.crew.crew_title import CrewTitle
from app.ui.base_widget import BaseWidget
from utils.i18n_utils import tr

from app.ui.chat.list.agent_chat_list_items import ChatListItem, MessageGroup, LoadState
from app.ui.chat.list.qml_agent_chat_list_model import QmlAgentChatListModel
from agent.chat.history.agent_chat_history_service import FastMessageHistoryService, message_saved
from agent.chat.history.agent_chat_storage import MessageLogHistory

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.data.workspace import Workspace


class QmlAgentChatListWidget(BaseWidget):
    """QML-based chat list widget with hardware-accelerated rendering.

    Features:
    - Dynamic heights with automatic layout
    - Pixel-perfect smooth scrolling (60 FPS)
    - Built-in virtualization for 100k+ messages
    - Component-based message delegates
    - Date grouping separators
    - Read status indicators
    - Theme switching support

    Signals:
        reference_clicked: Emitted when user clicks a reference (ref_type, ref_id)
        message_complete: Emitted when message finishes streaming (message_id, agent_name)
        load_more_requested: Emitted when user scrolls to top and more messages should load
    """

    # Configuration
    PAGE_SIZE = 200
    MAX_MODEL_ITEMS = 300
    NEW_DATA_CHECK_INTERVAL_MS = 500
    SCROLL_TOP_THRESHOLD = 50
    LOAD_MORE_DEBOUNCE_MS = 300  # Debounce delay for load more requests

    # Signals
    reference_clicked = Signal(str, str)  # ref_type, ref_id
    message_complete = Signal(str, str)  # message_id, agent_name
    load_more_requested = Signal()

    def __init__(self, workspace: "Workspace", parent=None):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        # QML Model
        self._model = QmlAgentChatListModel(self)

        # QML View widget
        self._quick_widget = QQuickWidget(self)
        self._quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)

        # Register context property for model access (matches _chatModel in QML)
        self._quick_widget.rootContext().setContextProperty("_chatModel", self._model)

        # Get correct QML path (qml is in app/ui/qml, widget is in app/ui/chat/list)
        qml_path = Path(__file__).parent.parent.parent / "qml" / "chat" / "AgentChatList.qml"

        if not qml_path.exists():
            logger.error(f"QML file not found at: {qml_path}")
            # Try fallback path
            qml_path = Path(__file__).parent.parent / "qml" / "chat" / "AgentChatList.qml"

        # Load QML
        self._quick_widget.setSource(QUrl.fromLocalFile(str(qml_path)))

        # Check for errors
        if self._quick_widget.status() == QQuickWidget.Error:
            errors = self._quick_widget.errors()
            for error in errors:
                logger.error(f"QML Error: {error.toString()}")
            logger.error("Failed to load QML")
            return

        # Get QML root object
        self._qml_root = self._quick_widget.rootObject()
        if not self._qml_root:
            logger.error("Failed to load QML root object")
            return

        logger.info("QML loaded successfully")

        # Connect QML signals to Python
        self._qml_root.referenceClicked.connect(self._on_qml_reference_clicked)
        self._qml_root.messageCompleted.connect(self._on_qml_message_completed)
        self._qml_root.loadMoreRequested.connect(self._on_qml_load_more)
        self._qml_root.scrollPositionChanged.connect(self._on_qml_scroll_position_changed)

        # State tracking
        self._load_state = LoadState()
        self._loading_older = False
        self._user_at_bottom = True

        # Crew member metadata cache
        self._crew_member_metadata: Dict[str, Dict[str, Any]] = {}
        self._agent_current_cards: Dict[str, str] = {}

        # Active skills tracking: {run_id: {message_id, skill_name, sender_name, state}}
        self._active_skills: Dict[str, Dict[str, Any]] = {}

        # History cache
        self._history: Optional[MessageLogHistory] = None

        # New data check timer - polls for new messages using active log count
        # NOTE: This is kept as backup but primary loading is driven by message_saved signal
        self._new_data_check_timer = QTimer(self)
        self._new_data_check_timer.timeout.connect(self._check_for_new_data)

        # Load more debounce timer - prevents excessive load requests during scroll
        self._load_more_timer = QTimer(self)
        self._load_more_timer.setSingleShot(True)
        self._load_more_timer.timeout.connect(self._do_load_older_messages)

        # For scroll position preservation
        self._first_visible_message_id_before_load: Optional[str] = None

        # Connect to message_saved signal for storage-driven refresh
        self._connect_to_storage_signals()

        # Setup UI and load data
        self._setup_ui()
        self._load_crew_member_metadata()
        self._load_recent_conversation()
        # Don't start the timer - rely on message_saved signal instead
        # self._start_new_data_check_timer()

    def _setup_ui(self):
        """Setup the widget layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)
        layout.addWidget(self._quick_widget)

    def _refresh_qml_model(self):
        """Force QML to refresh the model binding."""
        if self._qml_root:
            # Re-set the context property to trigger QML update
            self._quick_widget.rootContext().setContextProperty("_chatModel", None)
            self._quick_widget.rootContext().setContextProperty("_chatModel", self._model)

    # ─── QML Signal Handlers ─────────────────────────────────────────────

    @Slot(str, str)
    def _on_qml_reference_clicked(self, ref_type: str, ref_id: str):
        """Handle reference click from QML."""
        self.reference_clicked.emit(ref_type, ref_id)

    @Slot(str, str)
    def _on_qml_message_completed(self, message_id: str, agent_name: str):
        """Handle message completion from QML."""
        self.message_complete.emit(message_id, agent_name)

    @Slot()
    def _on_qml_load_more(self):
        """Handle load more request from QML (scroll to top) with debounce."""
        if not self._load_state.has_more_older or self._loading_older:
            return
        # Restart debounce timer
        self._load_more_timer.start(self.LOAD_MORE_DEBOUNCE_MS)

    def _do_load_older_messages(self):
        """Actually load older messages after debounce."""
        if not self._loading_older and self._load_state.has_more_older:
            self._load_older_messages()

    @Slot(bool)
    def _on_qml_scroll_position_changed(self, at_bottom: bool):
        """Handle scroll position change from QML."""
        self._user_at_bottom = at_bottom

    # ─── Data Loading (same as original implementation) ───────────────────

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
        """Handle project switch."""
        self._stop_new_data_check_timer()
        self.refresh_crew_member_metadata()
        self._load_state = LoadState()
        self._loading_older = False
        self._history = None
        self._model.clear()
        # Reconnect to storage signals for new project
        self._connect_to_storage_signals()
        self._load_recent_conversation()
        # Don't restart timer - rely on message_saved signal instead

    def refresh_crew_member_metadata(self):
        """Reload crew member metadata."""
        self._load_crew_member_metadata()

    def _connect_to_storage_signals(self):
        """Connect to storage signals for storage-driven refresh."""
        try:
            message_saved.connect(self._on_message_saved, weak=False)
            logger.debug("QML: Connected to message_saved signal")
        except Exception as e:
            logger.error(f"QML: Error connecting to message_saved signal: {e}")

    def _disconnect_from_storage_signals(self):
        """Disconnect from storage signals."""
        try:
            message_saved.disconnect(self._on_message_saved)
            logger.debug("QML: Disconnected from message_saved signal")
        except Exception:
            pass  # Signal might not be connected

    def _on_message_saved(self, sender, workspace_path: str, project_name: str, message_id: str,
                         gsn: int = 0, current_gsn: int = 0):
        """Handle message_saved signal from storage.

        This is called after a message is successfully written to storage.
        We trigger a data refresh to load the new message from storage.

        Enhanced with GSN (Global Sequence Number) support for archive-aware
        message tracking. The GSN allows correct message fetching even after
        archiving operations.

        Args:
            sender: Signal sender
            workspace_path: Path to workspace
            project_name: Name of project
            message_id: ID of the saved message
            gsn: Global sequence number of the saved message
            current_gsn: Current (latest) GSN in the system
        """
        # Only refresh if this message belongs to our current project
        if (workspace_path == self.workspace.workspace_path and
            project_name == self.workspace.project_name):
            # Update current GSN tracking
            if current_gsn > 0:
                self._load_state.current_gsn = current_gsn

            # Load new messages from storage using GSN-based fetching
            # Unlike the polling version, we always attempt to load (no _user_at_bottom check)
            # This ensures messages are loaded even when user is viewing history
            self._load_new_messages_from_history(gsn, current_gsn)

    def _clear_all_caches_and_model(self):
        """Clear all caches and the model."""
        self._model.clear()
        self._load_state.known_message_ids.clear()
        self._load_state.unique_message_count = 0
        self._load_state.total_loaded_count = 0
        self._load_state.min_loaded_gsn = 0
        self._load_state.has_more_older = False
        # Note: GSN tracking is NOT reset here to maintain state across UI refreshes
        # GSN reset only happens on project switch

    def _load_recent_conversation(self):
        """Load recent conversation from history.

        Enhanced with GSN tracking initialization for archive-aware
        message loading.
        """
        try:
            project = self.workspace.get_project()
            if not project:
                logger.warning("No project found, skipping history load")
                return

            history = self._get_history()
            if not history:
                logger.warning("Could not get history instance")
                return

            raw_messages = history.get_latest_messages(count=self.PAGE_SIZE)

            # Update load state
            self._load_state.active_log_count = history.storage.get_message_count()
            self._load_state.current_line_offset = self._load_state.active_log_count

            # Initialize GSN tracking if not already set
            if self._load_state.current_gsn == 0:
                try:
                    from agent.chat.history.agent_chat_history_service import FastMessageHistoryService
                    self._load_state.current_gsn = FastMessageHistoryService.get_current_gsn(
                        self.workspace.workspace_path,
                        self.workspace.project_name
                    )
                    logger.debug(f"Initialized current GSN: {self._load_state.current_gsn}")
                except Exception as e:
                    logger.debug(f"Could not initialize GSN tracking (using legacy mode): {e}")

            # Clear model for fresh load
            self._model.clear()
            self._load_state.known_message_ids.clear()
            self._load_state.unique_message_count = 0
            self._load_state.total_loaded_count = 0
            self._load_state.has_more_older = False

            if raw_messages:
                # Group messages by message_id (in chronological order)
                message_groups: Dict[str, MessageGroup] = {}
                max_gsn = 0
                min_gsn = float('inf')
                # Reverse to get chronological order (oldest first)
                for msg_data in reversed(raw_messages):
                    message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
                    if not message_id:
                        continue

                    # Track GSN range in loaded messages
                    msg_gsn = msg_data.get('metadata', {}).get('gsn', 0)
                    if msg_gsn > max_gsn:
                        max_gsn = msg_gsn
                    if msg_gsn > 0 and msg_gsn < min_gsn:
                        min_gsn = msg_gsn

                    if message_id not in message_groups:
                        message_groups[message_id] = MessageGroup()
                    message_groups[message_id].add_message(msg_data)

                # Update GSN tracking
                self._load_state.last_seen_gsn = max_gsn
                self._load_state.min_loaded_gsn = min_gsn if min_gsn != float('inf') else 0
                logger.debug(f"Updated GSN range: min={self._load_state.min_loaded_gsn}, max={self._load_state.last_seen_gsn}")

                # Convert to ordered list (in chronological order)
                ordered_messages = []
                for msg_data in reversed(raw_messages):
                    message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
                    if message_id in message_groups and message_id not in self._load_state.known_message_ids:
                        combined = message_groups[message_id].get_combined_message()
                        if combined:
                            ordered_messages.append(combined)
                            self._load_state.known_message_ids.add(message_id)

                # Load into model
                for msg_data in ordered_messages:
                    self._load_message_from_history(msg_data)

                self._load_state.unique_message_count = len(ordered_messages)
                self._load_state.total_loaded_count = len(ordered_messages)
                # Fix has_more_older logic: compare total loaded with total in storage
                total_count = history.get_total_count()
                self._load_state.has_more_older = self._load_state.total_loaded_count < total_count

                logger.info(f"Loaded {len(ordered_messages)} unique messages (total: {total_count})")

                # Force QML to update model binding
                self._refresh_qml_model()

                # Scroll to bottom after loading (force since user just opened/refreshed chat)
                # Use QTimer.singleShot to ensure QML has completed layout updates
                QTimer.singleShot(0, lambda: self._scroll_to_bottom(force=True))

            else:
                self._model.clear()
                self._load_state.known_message_ids.clear()
                logger.info("No messages found in history")

        except Exception as e:
            logger.error(f"Error loading recent conversation: {e}", exc_info=True)

    def _load_older_messages(self):
        """Load older messages when user scrolls to top."""
        if self._loading_older or not self._load_state.has_more_older:
            return

        self._loading_older = True
        self._qml_root.setProperty("isLoadingOlder", True)

        try:
            # Use enhanced history with GSN support
            from agent.chat.history.global_sequence_manager import get_enhanced_history

            enhanced_history = get_enhanced_history(
                self.workspace.workspace_path,
                self.workspace.project_name
            )

            # Use GSN-based cursor instead of line_offset
            max_gsn = self._load_state.min_loaded_gsn
            older_messages = enhanced_history.get_messages_before_gsn(max_gsn, count=self.PAGE_SIZE)

            if not older_messages:
                self._load_state.has_more_older = False
                return

            # Track min GSN in this batch for next load
            batch_min_gsn = self._load_state.min_loaded_gsn

            # Group and build items
            message_groups: Dict[str, MessageGroup] = {}
            for msg_data in older_messages:
                message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
                if not message_id:
                    continue

                # Track min GSN in this batch
                msg_gsn = msg_data.get('metadata', {}).get('gsn', 0)
                if msg_gsn > 0 and msg_gsn < batch_min_gsn:
                    batch_min_gsn = msg_gsn

                if message_id not in message_groups:
                    message_groups[message_id] = MessageGroup()
                message_groups[message_id].add_message(msg_data)

            items = []
            for message_id, group in message_groups.items():
                if message_id in self._load_state.known_message_ids:
                    continue

                combined_msg = group.get_combined_message()
                if combined_msg:
                    item = self._build_item_from_history(combined_msg)
                    if item:
                        items.append(item)
                        self._load_state.known_message_ids.add(message_id)

            if items:
                # Save the first visible message ID and item count before prepending for scroll position preservation
                self._first_visible_message_id_before_load = self._get_first_visible_message_id()
                self._item_count_before_load = self._model.rowCount()

                # Convert to QML format and prepend
                qml_items = [QmlAgentChatListModel.from_chat_list_item(item) for item in items]
                self._model.prepend_items(qml_items)

                self._load_state.unique_message_count += len(items)
                self._load_state.total_loaded_count += len(items)
                # Update GSN cursor only if it actually changed
                # If all messages have GSN=0, don't update cursor to avoid infinite loop
                if batch_min_gsn < self._load_state.min_loaded_gsn:
                    self._load_state.min_loaded_gsn = batch_min_gsn

                self._prune_model_bottom()

                # Restore scroll position after a delay to let QML update
                if self._first_visible_message_id_before_load:
                    QTimer.singleShot(0, self._restore_scroll_position)

                logger.debug(f"Prepended {len(items)} older messages, new min_gsn={self._load_state.min_loaded_gsn}")

            # Fix has_more_older logic: use total_loaded_count (not affected by prune)
            total_count = enhanced_history.get_total_count()
            self._load_state.has_more_older = self._load_state.total_loaded_count < total_count

        except Exception as e:
            logger.error(f"Error loading older messages: {e}", exc_info=True)
        finally:
            self._loading_older = False
            self._qml_root.setProperty("isLoadingOlder", False)

    def _prune_model_bottom(self):
        """Remove excess items from bottom."""
        excess = self._model.rowCount() - self.MAX_MODEL_ITEMS
        if excess > 0:
            for _ in range(excess):
                if self._model.rowCount() > 0:
                    item = self._model.get_item(self._model.rowCount() - 1)
                    if item:
                        msg_id = item.get(QmlAgentChatListModel.MESSAGE_ID)
                        if msg_id in self._load_state.known_message_ids:
                            self._load_state.known_message_ids.remove(msg_id)
                    self._model.remove_last_n(1)

    def _prune_model_top(self):
        """Remove excess items from top."""
        excess = self._model.rowCount() - self.MAX_MODEL_ITEMS
        if excess > 0:
            for _ in range(excess):
                if self._model.rowCount() > 0:
                    item = self._model.get_item(0)
                    if item:
                        msg_id = item.get(QmlAgentChatListModel.MESSAGE_ID)
                        if msg_id in self._load_state.known_message_ids:
                            self._load_state.known_message_ids.remove(msg_id)
                    self._model.remove_first_n(1)
            self._load_state.has_more_older = True

    # ─── Message Building ─────────────────────────────────────────────────

    def _build_item_from_history(self, msg_data: Dict[str, Any]) -> Optional[ChatListItem]:
        """Build a ChatListItem from history data.

        History JSON has fields at both top-level and in metadata.
        We check top-level first, then fallback to metadata.
        """
        try:
            metadata = msg_data.get("metadata", {})
            content_list = msg_data.get("content", [])

            # Check both top-level and metadata for fields (top-level takes precedence)
            message_id = msg_data.get("message_id") or metadata.get("message_id", "")
            sender_id = msg_data.get("sender_id") or metadata.get("sender_id", "unknown")
            sender_name = msg_data.get("sender_name") or metadata.get("sender_name", sender_id)
            timestamp = msg_data.get("timestamp") or metadata.get("timestamp")

            if not message_id:
                logger.warning(f"No message_id in msg_data: {msg_data.keys()}")
                return None

            logger.debug(f"Parsing message: {message_id[:8]}... from {sender_name}")

            is_user = sender_id.lower() == "user"

            if is_user:
                text_content = ""
                for content_item in content_list:
                    if isinstance(content_item, dict):
                        if content_item.get("content_type") == "text":
                            text_content = content_item.get("data", {}).get("text", "")
                            break

                logger.debug(f"  User message: {text_content[:50]}...")
                return ChatListItem(
                    message_id=message_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    is_user=True,
                    user_content=text_content,
                )
            else:
                structured_content = []
                # Track skills by name for merging
                skills_by_name: Dict[str, List[Dict[str, Any]]] = {}
                # Track tool_call entries that might belong to skills
                tool_entries: List[Dict[str, Any]] = []

                for content_item in content_list:
                    if isinstance(content_item, dict):
                        content_type = content_item.get("content_type")
                        # Group skill entries by skill_name for merging
                        if content_type == "skill":
                            skill_name = content_item.get("data", {}).get("skill_name", "")
                            if skill_name:
                                if skill_name not in skills_by_name:
                                    skills_by_name[skill_name] = []
                                skills_by_name[skill_name].append(content_item)
                            else:
                                # Skill without name, add directly
                                try:
                                    sc = StructureContent.from_dict(content_item)
                                    structured_content.append(sc)
                                except Exception as e:
                                    logger.debug(f"Failed to load structured content: {e}")
                        elif content_type == "tool_call":
                            # Collect tool_call entries for potential skill association
                            tool_entries.append(content_item)
                        else:
                            # Non-skill, non-tool content, add directly
                            try:
                                sc = StructureContent.from_dict(content_item)
                                structured_content.append(sc)
                            except Exception as e:
                                logger.debug(f"Failed to load structured content: {e}")

                # Merge skill entries and add to structured_content
                for skill_name, skill_entries in skills_by_name.items():
                    merged_skill = self._merge_skill_entries(skill_name, skill_entries, tool_entries)
                    if merged_skill:
                        structured_content.append(merged_skill)

                # Add timestamp to metadata for QML
                if timestamp and "timestamp" not in metadata:
                    metadata["timestamp"] = timestamp

                agent_message = ChatAgentMessage(
                    sender_id=sender_id,
                    sender_name=sender_name,
                    message_id=message_id,
                    metadata=metadata,
                    structured_content=structured_content,
                )

                agent_color, agent_icon, crew_member_data = self._resolve_agent_metadata(
                    sender_name, metadata
                )

                logger.debug(f"  Agent message with {len(structured_content)} content items")
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
        """Load a single message from history into model."""
        item = self._build_item_from_history(msg_data)
        if item:
            qml_item = QmlAgentChatListModel.from_chat_list_item(item)
            self._model.add_item(qml_item)

    # ─── Skill Content Merging ────────────────────────────────────────────
    # Common utilities for merging skill content entries (used by both
    # historical loading and real-time updates)

    def _get_skill_state_priority(self) -> Dict[str, int]:
        """Get the priority mapping for skill execution states.

        Higher priority states override lower ones during merging.

        Returns:
            Dictionary mapping state values to priority levels (higher = more important)
        """
        from agent.chat.content import SkillExecutionState
        return {
            SkillExecutionState.ERROR.value: 4,
            SkillExecutionState.COMPLETED.value: 3,
            SkillExecutionState.IN_PROGRESS.value: 2,
            SkillExecutionState.PENDING.value: 1,
        }

    def _determine_base_skill_entry(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Determine which skill entry should be used as the base for merging.

        Uses state priority to select the most important entry as the base.
        If all entries have the same priority (e.g., all in_progress),
        the last entry (most recent) is used.

        Args:
            entries: List of skill content entries (dict format)

        Returns:
            The entry that should be used as base
        """
        state_priority = self._get_skill_state_priority()

        # Sort entries by state priority (highest first)
        sorted_entries = sorted(
            entries,
            key=lambda e: state_priority.get(
                e.get("data", {}).get("state", ""),
                0
            ),
            reverse=True
        )

        # Check if all entries have the same state priority
        highest_priority = state_priority.get(
            sorted_entries[0].get("data", {}).get("state", ""),
            0
        )
        all_same_priority = all(
            state_priority.get(e.get("data", {}).get("state", ""), 0) == highest_priority
            for e in entries
        )

        # If all are in_progress with same priority, use the last (most recent)
        # Otherwise use the highest priority entry
        if all_same_priority and highest_priority == state_priority.get("in_progress", 2):
            return entries[-1]
        else:
            return sorted_entries[0]

    def _merge_child_contents(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge child contents from multiple skill entries.

        Collects all child_contents from entries and removes duplicates
        based on content_id.

        Args:
            entries: List of skill content entries (dict format)

        Returns:
            Merged list of child contents with duplicates removed
        """
        child_contents = []
        seen_content_ids = set()

        for entry in entries:
            entry_children = entry.get("data", {}).get("child_contents", [])
            for child in entry_children:
                content_id = child.get("content_id")
                if content_id:
                    if content_id not in seen_content_ids:
                        child_contents.append(child)
                        seen_content_ids.add(content_id)
                else:
                    # No content_id, just append (can't deduplicate)
                    child_contents.append(child)

        return child_contents

    def _create_skill_content_from_entry(
        self,
        entry: Dict[str, Any],
        skill_name: str,
        child_contents: List[Dict[str, Any]] = None
    ) -> 'StructureContent':
        """Create a SkillContent from an entry dictionary.

        Args:
            entry: The skill entry (dict format)
            skill_name: The name of the skill
            child_contents: Optional child contents to include

        Returns:
            A SkillContent object
        """
        from agent.chat.content import SkillContent, SkillExecutionState, ContentStatus

        base_data = entry.get("data", {})
        final_state = base_data.get("state", SkillExecutionState.IN_PROGRESS.value)

        # Map skill execution state to content status
        if final_state == SkillExecutionState.COMPLETED.value:
            final_status = ContentStatus.COMPLETED
        elif final_state == SkillExecutionState.ERROR.value:
            final_status = ContentStatus.FAILED
        elif final_state == SkillExecutionState.IN_PROGRESS.value:
            final_status = ContentStatus.UPDATING
        else:
            final_status = ContentStatus.CREATING

        return SkillContent(
            content_type=ContentType(entry.get("content_type", "skill")),
            title=entry.get("title", f"Skill: {skill_name}"),
            description=entry.get("description", f"Skill execution: {skill_name}"),
            content_id=entry.get("content_id"),
            status=final_status,
            metadata=entry.get("metadata", {}),
            skill_name=skill_name,
            skill_description=base_data.get("description", ""),
            state=SkillExecutionState(final_state) if isinstance(final_state, str) else final_state,
            progress_text=base_data.get("progress_text", ""),
            progress_percentage=base_data.get("progress_percentage"),
            result=base_data.get("result", ""),
            error_message=base_data.get("error_message", ""),
            child_contents=child_contents if child_contents is not None else [],
            run_id=base_data.get("run_id", ""),
        )

    def _merge_skill_entries(self, skill_name: str, skill_entries: List[Dict[str, Any]],
                           tool_entries: List[Dict[str, Any]] = None) -> Optional['StructureContent']:
        """Merge multiple skill entries into a single SkillContent.

        Args:
            skill_name: The name of the skill
            skill_entries: List of skill content dictionaries
            tool_entries: List of tool_call content dictionaries to associate as children

        Returns:
            A merged SkillContent or None if merging fails
        """
        if not skill_entries:
            return None

        tool_entries = tool_entries or []

        # Use common utilities to determine base entry and merge child contents
        base_entry = self._determine_base_skill_entry(skill_entries)
        child_contents = self._merge_child_contents(skill_entries)

        # Associate tool_call entries as children based on progress_text mentions
        # For example, if skill progress_text says "Executing tool [1] - execute_skill_script"
        # and there's a tool_call with tool_name="execute_skill_script", associate them
        associated_tools = set()
        for skill_entry in skill_entries:
            progress_text = skill_entry.get("data", {}).get("progress_text", "")
            if progress_text:
                # Extract tool name from progress_text like "Executing tool [1] - execute_skill_script"
                for tool_entry in tool_entries:
                    tool_name = tool_entry.get("data", {}).get("tool_name", "")
                    if tool_name and tool_name in progress_text and tool_entry.get("content_id") not in associated_tools:
                        child_contents.append(tool_entry)
                        associated_tools.add(tool_entry.get("content_id"))

        # For any remaining tool_entries, add them as children (they're part of the same skill execution context)
        for tool_entry in tool_entries:
            if tool_entry.get("content_id") not in associated_tools:
                # Only add if it seems related (e.g., skill might have used this tool)
                # For now, add all tool_calls from the same message as skill children
                child_contents.append(tool_entry)

        # Use common utility to create final SkillContent
        return self._create_skill_content_from_entry(base_entry, skill_name, child_contents)

    # ─── Crew Member Metadata ────────────────────────────────────────────

    def _load_crew_member_metadata(self):
        """Load crew member metadata from project."""
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
            logger.error(f"Error loading crew members: {e}")
            self._crew_member_metadata = {}

    def _resolve_agent_metadata(self, sender: str, message_metadata: Optional[Dict[str, Any]] = None):
        """Resolve agent color, icon, and metadata."""
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
            crew_title_raw = sender_crew_member.config.metadata.get("crew_title", normalized_sender)

            # Get localized display name for crew title
            crew_title_display = self._get_crew_title_display(crew_title_raw)

            crew_member_data = {
                "name": sender_crew_member.config.name,
                "description": sender_crew_member.config.description,
                "color": agent_color,
                "icon": agent_icon,
                "crew_title": crew_title_raw,
                "crew_title_display": crew_title_display,
            }
        else:
            if message_metadata:
                agent_color = message_metadata.get("color", agent_color)
                agent_icon = message_metadata.get("icon", agent_icon)
                crew_title_raw = message_metadata.get("crew_title", normalized_sender)
                crew_title_display = self._get_crew_title_display(crew_title_raw)
                crew_member_data = dict(message_metadata)
                crew_member_data["crew_title_display"] = crew_title_display
        return agent_color, agent_icon, crew_member_data

    def _get_crew_title_display(self, crew_title: str) -> str:
        """Get localized display name for crew title."""
        try:
            crew_title_obj = CrewTitle.create_from_title(crew_title)
            return crew_title_obj.get_title_display()
        except Exception:
            # Fallback to formatted title (replace underscores with spaces, title case)
            return crew_title.replace("_", " ").title() if crew_title else ""

    # ─── Public API ───────────────────────────────────────────────────────

    def add_user_message(self, content: str):
        """Add a user message to the chat."""
        message_id = str(uuid.uuid4())

        item = {
            QmlAgentChatListModel.MESSAGE_ID: message_id,
            QmlAgentChatListModel.SENDER_ID: "user",
            QmlAgentChatListModel.SENDER_NAME: tr("User"),
            QmlAgentChatListModel.IS_USER: True,
            QmlAgentChatListModel.CONTENT: content,
            QmlAgentChatListModel.AGENT_COLOR: "#4a90e2",
            QmlAgentChatListModel.AGENT_ICON: "\ue6b3",
            QmlAgentChatListModel.CREW_METADATA: {},
            QmlAgentChatListModel.STRUCTURED_CONTENT: [],
            QmlAgentChatListModel.CONTENT_TYPE: "text",
            QmlAgentChatListModel.IS_READ: True,
            QmlAgentChatListModel.TIMESTAMP: None,
            QmlAgentChatListModel.DATE_GROUP: "",
        }

        self._model.add_item(item)
        self._scroll_to_bottom(force=True)  # User sent a message, always scroll
        return message_id

    def append_message(self, sender: str, message: str, message_id: str = None):
        """Append a message to the chat."""
        if not message:
            return None

        is_user = sender.lower() in ["user", tr("用户").lower(), tr("user").lower()]
        if is_user:
            return self.add_user_message(message)

        if not message_id:
            message_id = str(uuid.uuid4())

        agent_color, agent_icon, crew_member_data = self._resolve_agent_metadata(sender)

        item = {
            QmlAgentChatListModel.MESSAGE_ID: message_id,
            QmlAgentChatListModel.SENDER_ID: sender,
            QmlAgentChatListModel.SENDER_NAME: sender,
            QmlAgentChatListModel.IS_USER: False,
            QmlAgentChatListModel.CONTENT: message,
            QmlAgentChatListModel.AGENT_COLOR: agent_color,
            QmlAgentChatListModel.AGENT_ICON: agent_icon,
            QmlAgentChatListModel.CREW_METADATA: crew_member_data,
            QmlAgentChatListModel.STRUCTURED_CONTENT: [],
            QmlAgentChatListModel.CONTENT_TYPE: "text",
            QmlAgentChatListModel.IS_READ: True,
            QmlAgentChatListModel.TIMESTAMP: None,
            QmlAgentChatListModel.DATE_GROUP: "",
        }

        self._model.add_item(item)
        self._scroll_to_bottom(force=True)  # User action, always scroll
        return message_id

    def update_streaming_message(self, message_id: str, content: str):
        """Update a streaming message."""
        self._model.update_item(message_id, {
            QmlAgentChatListModel.CONTENT: content,
        })
        self._scroll_to_bottom(force=True)  # Streaming update, always scroll

    def get_or_create_agent_card(self, message_id: str, agent_name: str, title=None):
        """Get or create an agent message card."""
        existing_row = self._model.get_row_by_message_id(message_id)
        if existing_row is not None:
            return message_id

        agent_color, agent_icon, crew_member_data = self._resolve_agent_metadata(agent_name)

        item = {
            QmlAgentChatListModel.MESSAGE_ID: message_id,
            QmlAgentChatListModel.SENDER_ID: agent_name,
            QmlAgentChatListModel.SENDER_NAME: agent_name,
            QmlAgentChatListModel.IS_USER: False,
            QmlAgentChatListModel.CONTENT: "",
            QmlAgentChatListModel.AGENT_COLOR: agent_color,
            QmlAgentChatListModel.AGENT_ICON: agent_icon,
            QmlAgentChatListModel.CREW_METADATA: crew_member_data,
            QmlAgentChatListModel.STRUCTURED_CONTENT: [],
            QmlAgentChatListModel.CONTENT_TYPE: "text",
            QmlAgentChatListModel.IS_READ: True,
            QmlAgentChatListModel.TIMESTAMP: None,
            QmlAgentChatListModel.DATE_GROUP: "",
        }

        self._model.add_item(item)
        self._agent_current_cards[agent_name] = message_id
        self._scroll_to_bottom(force=True)  # AI started responding, always scroll
        return message_id

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
        """Update an agent message card."""
        updates = {}

        # Update content
        if content is not None:
            item = self._model.get_item(self._model.get_row_by_message_id(message_id) or 0)
            if item:
                current_content = item.get(QmlAgentChatListModel.CONTENT, "")
                new_content = (current_content + content) if append else content
                updates[QmlAgentChatListModel.CONTENT] = new_content

        # Update structured content
        if structured_content is not None:
            item = self._model.get_item(self._model.get_row_by_message_id(message_id) or 0)
            if item:
                current_structured = item.get(QmlAgentChatListModel.STRUCTURED_CONTENT, [])

                # Handle different input types
                if isinstance(structured_content, StructureContent):
                    items = [structured_content.to_dict()]
                elif isinstance(structured_content, list):
                    items = []
                    for sc in structured_content:
                        if hasattr(sc, 'to_dict'):
                            items.append(sc.to_dict())
                        elif isinstance(sc, dict):
                            items.append(sc)
                else:
                    items = []

                # Filter out typing indicators if complete
                if is_complete:
                    current_structured = [
                        sc for sc in current_structured
                        if sc.get('content_type') != 'typing'
                    ]

                new_structured = current_structured + items
                updates[QmlAgentChatListModel.STRUCTURED_CONTENT] = new_structured

                # Update content type based on structured content
                if items:
                    primary_type = items[0].get('content_type', 'text')
                    updates[QmlAgentChatListModel.CONTENT_TYPE] = primary_type

        # Handle error
        if error:
            error_text = f"❌ Error: {error}"
            updates[QmlAgentChatListModel.CONTENT] = error_text
            updates[QmlAgentChatListModel.CONTENT_TYPE] = "error"

        if updates:
            self._model.update_item(message_id, updates)

        self._scroll_to_bottom(force=True)  # Real-time AI response update, always scroll

    @Slot(object, object)
    def handle_stream_event(self, event, session):
        """Handle stream events."""
        if event.event_type == "error":
            self._handle_error_event(event)
        elif event.event_type == "agent_response":
            self._handle_agent_response_event(event)
        elif event.event_type in ["skill_start", "skill_progress", "skill_end", "skill_error"]:
            self._handle_skill_event(event)
        elif event.event_type in ["tool_start", "tool_progress", "tool_end", "tool_error"]:
            self._handle_tool_event(event)
        elif event.event_type in ["crew_member_typing", "crew_member_typing_end"]:
            self._handle_typing_event(event)
        elif hasattr(event, "content") and event.content:
            self._handle_content_event(event)

    def _handle_error_event(self, event):
        """Handle error events."""
        from agent.chat.content import ErrorContent

        run_id = getattr(event, "run_id", "")

        # Prepare error content dict
        # Check if event has content (StructureContent) or use data fallback
        if hasattr(event, 'content') and event.content:
            if hasattr(event.content, 'to_dict') and callable(event.content.to_dict):
                error_dict = event.content.to_dict()
            else:
                error_dict = ErrorContent(error_message=str(event.content)).to_dict()
        else:
            error_content = event.data.get("content", event.data.get("error", "Unknown error"))
            error_dict = ErrorContent(error_message=error_content).to_dict()

        # If there's an active skill, add error to its child_contents
        if run_id and run_id in self._active_skills:
            skill_info = self._active_skills[run_id]
            message_id = skill_info["message_id"]

            # Add to child contents
            skill_info["child_contents"].append(error_dict)

            # Update the skill to show the new child content
            # Pass run_id to ensure we only update the matching skill
            self._add_child_to_skill(message_id, error_dict, run_id=run_id)
            return

        # No active skill - handle as standalone error
        message_id = str(uuid.uuid4())
        self.get_or_create_agent_card(message_id, "System", "System")
        self.update_agent_card(
            message_id,
            structured_content=error_dict,
            error=event.data.get("content", event.data.get("error", "Unknown error")),
        )

    def _handle_agent_response_event(self, event):
        """Handle agent response events."""
        from agent.chat.content import TextContent

        content = event.data.get("content", "")
        sender_name = event.data.get("sender_name", "Unknown")
        sender_id = event.data.get("sender_id", sender_name.lower())
        session_id = event.data.get("session_id", "unknown")
        run_id = getattr(event, "run_id", "")

        if sender_id == "user":
            return

        # Prepare text content dict
        text_dict = TextContent(text=content).to_dict()

        # If there's an active skill, add text to its child_contents
        if run_id and run_id in self._active_skills:
            skill_info = self._active_skills[run_id]
            message_id = skill_info["message_id"]

            # Add to child contents
            skill_info["child_contents"].append(text_dict)

            # Update the skill to show the new child content
            # Pass run_id to ensure we only update the matching skill
            self._add_child_to_skill(message_id, text_dict, run_id=run_id)
            return

        # No active skill - handle as standalone content
        message_id = event.data.get("message_id")
        if not message_id:
            message_id = f"response_{session_id}_{uuid.uuid4()}"

        self.get_or_create_agent_card(message_id, sender_name, sender_name)
        self.update_agent_card(message_id, structured_content=text_dict)

    def _handle_skill_event(self, event):
        """Handle skill events - tracks skill lifecycle with start/progress/end/error.

        Each skill execution is represented by a single SkillContent that:
        - Gets created on skill_start
        - Gets updated on skill_progress
        - Gets finalized on skill_end or skill_error
        - Collects child contents (tool calls, etc.) during execution
        """
        from agent.chat.content import SkillContent, SkillExecutionState, ContentStatus

        # Extract data from event content (SkillContent is already in event.content)
        skill_content = getattr(event, 'content', None)
        run_id = getattr(event, "run_id", "")

        if not skill_content or not isinstance(skill_content, SkillContent):
            # Fallback to data-based parsing for legacy events
            skill_name = event.data.get("skill_name", "Unknown")
            sender_name = event.data.get("sender_name", "Unknown")
            sender_id = event.data.get("sender_id", sender_name.lower())
            run_id = run_id or event.data.get("run_id", "")
            message_id = event.data.get("message_id") or f"skill_{run_id}_{skill_name}"

            if sender_id == "user":
                return

            # Determine state based on event type
            if event.event_type == "skill_start":
                state = SkillExecutionState.IN_PROGRESS
                progress_text = "Starting execution..."
                progress_percentage = None
                result = ""
                error_message = ""
            elif event.event_type == "skill_progress":
                state = SkillExecutionState.IN_PROGRESS
                progress_text = event.data.get("progress_text", "Processing...")
                progress_percentage = event.data.get("progress_percentage")
                result = ""
                error_message = ""
            elif event.event_type == "skill_end":
                state = SkillExecutionState.COMPLETED
                progress_text = ""
                progress_percentage = 100
                result = event.data.get("result", "")
                error_message = ""
            elif event.event_type == "skill_error":
                state = SkillExecutionState.ERROR
                progress_text = ""
                progress_percentage = None
                result = ""
                error_message = event.data.get("error", "Execution failed")
            else:
                return  # Unknown event type

            skill_content = SkillContent(
                skill_name=skill_name,
                state=state,
                progress_text=progress_text,
                progress_percentage=progress_percentage,
                result=result,
                error_message=error_message,
                run_id=run_id,
                title=f"Skill: {skill_name}",
                description=f"Skill execution: {skill_name}",
            )
        else:
            # Use event.content directly (SkillContent from skill_chat.py)
            # run_id is now always set in skill_chat.py, no need for fallback
            skill_name = skill_content.skill_name
            sender_name = getattr(event, 'sender_name', 'Unknown')
            sender_id = getattr(event, 'sender_id', sender_name.lower())
            message_id = f"skill_{run_id}_{skill_name}"

            if sender_id == "user":
                return

        # Handle different event types
        if event.event_type == "skill_start":
            # Track the active skill
            self._active_skills[run_id] = {
                "message_id": message_id,
                "skill_name": skill_name,
                "sender_name": sender_name,
                "state": SkillExecutionState.IN_PROGRESS,
                "child_contents": [],
            }
            # Create or update the skill card
            self.get_or_create_agent_card(message_id, sender_name, sender_name)
            self._update_skill_content(message_id, skill_content, create_new=True)

        elif event.event_type == "skill_progress":
            # Update the active skill
            if run_id in self._active_skills:
                self._active_skills[run_id]["state"] = SkillExecutionState.IN_PROGRESS
                self._update_skill_content(message_id, skill_content)
            else:
                # Skill progress without start - create new
                self._active_skills[run_id] = {
                    "message_id": message_id,
                    "skill_name": skill_name,
                    "sender_name": sender_name,
                    "state": SkillExecutionState.IN_PROGRESS,
                    "child_contents": [],
                }
                self.get_or_create_agent_card(message_id, sender_name, sender_name)
                self._update_skill_content(message_id, skill_content, create_new=True)

        elif event.event_type == "skill_end":
            # Finalize the skill
            if run_id in self._active_skills:
                self._active_skills[run_id]["state"] = SkillExecutionState.COMPLETED
                # Build final skill content with all child contents
                skill_content.child_contents = self._active_skills[run_id]["child_contents"]
                self._update_skill_content(message_id, skill_content)
                # Remove from active skills
                del self._active_skills[run_id]
            else:
                # Skill end without start - create new
                self.get_or_create_agent_card(message_id, sender_name, sender_name)
                self._update_skill_content(message_id, skill_content, create_new=True)

        elif event.event_type == "skill_error":
            # Finalize the skill with error
            if run_id in self._active_skills:
                self._active_skills[run_id]["state"] = SkillExecutionState.ERROR
                # Build final skill content with all child contents
                skill_content.child_contents = self._active_skills[run_id]["child_contents"]
                self._update_skill_content(message_id, skill_content)
                # Remove from active skills
                del self._active_skills[run_id]
            else:
                # Skill error without start - create new
                self.get_or_create_agent_card(message_id, sender_name, sender_name)
                self._update_skill_content(message_id, skill_content, create_new=True)

    def _update_skill_content(self, message_id: str, skill_content, create_new=False):
        """Update existing skill content with new state.

        Uses the same merging strategy as _merge_skill_entries to ensure
        consistency between historical loading and real-time updates.

        Args:
            message_id: The message ID containing the skill
            skill_content: New SkillContent with updated state
            create_new: If True, always create new content instead of replacing
        """
        from agent.chat.content import SkillContent, SkillExecutionState, ContentStatus

        item = self._model.get_item(self._model.get_row_by_message_id(message_id) or 0)
        if not item:
            return

        current_structured = item.get(QmlAgentChatListModel.STRUCTURED_CONTENT, [])

        # Check for existing skill with same run_id or skill_name
        existing_skill_entry = None
        existing_skill_index = -1
        for i, sc in enumerate(current_structured):
            if sc.get("content_type") == "skill":
                sc_data = sc.get("data", {})
                # Match by run_id first, then by skill_name
                if (sc_data.get("run_id") == skill_content.run_id and skill_content.run_id) or \
                   (sc_data.get("skill_name") == skill_content.skill_name):
                    existing_skill_entry = sc
                    existing_skill_index = i
                    break

        if existing_skill_entry is not None:
            # Found existing skill - merge using the same logic as _merge_skill_entries
            # This ensures real-time updates use the same merging strategy as historical loading
            merged_entry = self._merge_skill_content_with_existing(
                existing_skill_entry,
                skill_content
            )
            new_structured = list(current_structured)
            new_structured[existing_skill_index] = merged_entry
        elif create_new:
            # No existing skill and create_new is True - append new
            new_structured = list(current_structured)
            new_structured.append(skill_content.to_dict())
        else:
            # No existing skill and create_new is False - append anyway
            new_structured = list(current_structured)
            new_structured.append(skill_content.to_dict())

        self._model.update_item(message_id, {
            QmlAgentChatListModel.STRUCTURED_CONTENT: new_structured,
        })

    def _merge_skill_content_with_existing(self, existing_entry: Dict[str, Any], new_content) -> Dict[str, Any]:
        """Merge existing skill entry with new skill content.

        Uses the same merging strategy as _merge_skill_entries to ensure
        consistency between historical loading and real-time updates.

        Args:
            existing_entry: Existing skill entry (dict format from storage)
            new_content: New SkillContent object

        Returns:
            Merged skill entry in dict format
        """
        from agent.chat.content import SkillExecutionState

        existing_data = existing_entry.get("data", {})
        existing_state = existing_data.get("state", SkillExecutionState.PENDING.value)
        new_state = new_content.state.value if isinstance(new_content.state, SkillExecutionState) else new_content.state

        # Get state priority using common utility
        state_priority = self._get_skill_state_priority()
        existing_priority = state_priority.get(existing_state, 0)
        new_priority = state_priority.get(new_state, 0)

        # Determine which entry to use as base based on state priority
        # Higher priority state wins (e.g., error overrides in_progress)
        if new_priority > existing_priority:
            # New state has higher priority, use new content as base
            # But preserve child_contents from existing if new doesn't have them
            if not new_content.child_contents:
                new_content.child_contents = existing_data.get("child_contents", [])
            merged_dict = new_content.to_dict()

        elif new_priority < existing_priority:
            # Existing state has higher priority, keep existing but update certain fields
            # Update progress_text if new is in_progress and existing is also in_progress
            if (new_state == SkillExecutionState.IN_PROGRESS.value and
                existing_state == SkillExecutionState.IN_PROGRESS.value):
                # Both are in_progress, update with latest progress info
                merged_dict = dict(existing_entry)
                merged_data = dict(merged_dict.get("data", {}))
                merged_data.update({
                    "progress_text": new_content.progress_text,
                    "progress_percentage": new_content.progress_percentage,
                })
                # Merge child contents using common utility
                if new_content.child_contents:
                    # Combine existing children with new children
                    all_children = []
                    # Add existing children
                    for child in existing_data.get("child_contents", []):
                        all_children.append(child)
                    # Add new children not already present
                    existing_ids = {c.get("content_id") for c in all_children if c.get("content_id")}
                    for child in new_content.child_contents:
                        child_id = child.get("content_id") if isinstance(child, dict) else None
                        if child_id:
                            if child_id not in existing_ids:
                                all_children.append(child)
                        else:
                            # No content_id, just append
                            all_children.append(child)
                    merged_data["child_contents"] = all_children
                merged_dict["data"] = merged_data

            else:
                # Different states but existing has higher priority - keep existing unchanged
                merged_dict = existing_entry

        else:
            # Same priority - use the new content as it's more recent
            # But preserve and merge child_contents from existing
            if not new_content.child_contents:
                new_content.child_contents = existing_data.get("child_contents", [])
            else:
                # Merge child contents using common utility
                all_children = []
                # Add existing children
                for child in existing_data.get("child_contents", []):
                    all_children.append(child)
                # Add new children not already present
                existing_ids = {c.get("content_id") for c in all_children if c.get("content_id")}
                for child in new_content.child_contents:
                    child_id = child.get("content_id") if isinstance(child, dict) else None
                    if child_id:
                        if child_id not in existing_ids:
                            all_children.append(child)
                    else:
                        # No content_id, just append
                        all_children.append(child)
                new_content.child_contents = all_children
            merged_dict = new_content.to_dict()

        return merged_dict

    def _handle_tool_event(self, event):
        """Handle tool events - adds them as child contents to active skills.

        Tool events (tool_start, tool_progress, tool_end, tool_error) are
        associated with the active skill via run_id and stored as child contents.
        """
        run_id = getattr(event, "run_id", "")

        # Check if this tool belongs to an active skill
        if run_id not in self._active_skills:
            # No active skill - handle as standalone tool event
            # This shouldn't happen in normal flow but handle gracefully
            logger.debug(f"Tool event without active skill: run_id={run_id}")
            return

        skill_info = self._active_skills[run_id]
        message_id = skill_info["message_id"]

        # Create tool content from event
        from agent.chat.content import ToolCallContent

        tool_content = None
        if event.event_type == "tool_start":
            tool_content = ToolCallContent(
                tool_name=getattr(event, 'tool_name', event.data.get("tool_name", "unknown")),
                tool_input=event.data.get("tool_input", {}),
                tool_status="started",
            )
        elif event.event_type == "tool_progress":
            # For progress, we might update existing tool content or create a progress entry
            # For now, just track it
            pass
        elif event.event_type == "tool_end":
            tool_content = ToolCallContent(
                tool_name=getattr(event, 'tool_name', event.data.get("tool_name", "unknown")),
                tool_input=event.data.get("tool_input", {}),
                tool_status="completed",
                result=event.data.get("result"),
            )
        elif event.event_type == "tool_error":
            tool_content = ToolCallContent(
                tool_name=getattr(event, 'tool_name', event.data.get("tool_name", "unknown")),
                tool_input=event.data.get("tool_input", {}),
                tool_status="failed",
                error=event.data.get("error", "Tool execution failed"),
            )

        if tool_content:
            # Add to child contents
            tool_dict = tool_content.to_dict()
            skill_info["child_contents"].append(tool_dict)

            # Update the skill to show the new child content
            # Pass run_id to ensure we only update the matching skill
            self._add_child_to_skill(message_id, tool_dict, run_id=run_id)

    def _add_child_to_skill(self, message_id: str, child_content: Dict[str, Any], run_id: str = None):
        """Add a child content to the skill's child_contents list.

        Args:
            message_id: The message ID containing the skill
            child_content: The child content dictionary to add
            run_id: Optional run_id to identify which skill to update.
                    If not provided, adds to all skills (legacy behavior).
        """
        from agent.chat.content import SkillContent

        item = self._model.get_item(self._model.get_row_by_message_id(message_id) or 0)
        if not item:
            return

        current_structured = item.get(QmlAgentChatListModel.STRUCTURED_CONTENT, [])
        new_structured = []

        for sc in current_structured:
            if sc.get("content_type") == "skill":
                sc_data = sc.get("data", {})
                # If run_id is provided, only update matching skills
                if run_id is not None:
                    if sc_data.get("run_id") != run_id:
                        # Not the target skill, keep as-is
                        new_structured.append(sc)
                        continue

                # Add child content to the skill
                new_sc = dict(sc)
                sc_data = dict(new_sc.get("data", {}))
                child_contents = list(sc_data.get("child_contents", []))

                # Avoid duplicates by content_id
                child_id = child_content.get("content_id")
                if child_id:
                    existing_ids = {c.get("content_id") for c in child_contents if c.get("content_id")}
                    if child_id not in existing_ids:
                        child_contents.append(child_content)
                else:
                    # No content_id, just append
                    child_contents.append(child_content)

                sc_data["child_contents"] = child_contents
                new_sc["data"] = sc_data
                new_structured.append(new_sc)
            else:
                new_structured.append(sc)

        self._model.update_item(message_id, {
            QmlAgentChatListModel.STRUCTURED_CONTENT: new_structured,
        })

    def _handle_typing_event(self, event):
        """Handle crew_member_typing events to show/hide typing indicator."""
        from agent.chat.content import TypingContent, TypingState

        sender_id = getattr(event, "sender_id", "")
        sender_name = getattr(event, "sender_name", "")

        if not sender_id or sender_id == "user":
            return

        # Use run_id as the message_id since all events in a session share the same ID
        run_id = getattr(event, "run_id", "")
        if not run_id:
            return

        message_id = run_id

        if event.event_type == "crew_member_typing":
            # Create card with typing indicator
            self.get_or_create_agent_card(message_id, sender_name, sender_name)
            # Add TypingContent with START state
            typing_content = TypingContent(state=TypingState.START)
            self.update_agent_card(
                message_id,
                structured_content=typing_content,
                is_complete=False,
            )
            logger.debug(f"Added typing indicator for {sender_name} (message_id: {message_id})")
        elif event.event_type == "crew_member_typing_end":
            # Remove typing indicator by filtering it out
            item = self._model.get_item_by_message_id(message_id)
            if item:
                # Remove typing content from structured_content
                current_structured = item.get(QmlAgentChatListModel.STRUCTURED_CONTENT, [])
                filtered_structured = [
                    sc for sc in current_structured
                    if sc.get("content_type") != "typing"
                ]
                self._model.update_item(message_id, {
                    QmlAgentChatListModel.STRUCTURED_CONTENT: filtered_structured,
                })
                logger.debug(f"Removed typing indicator for {sender_name} (message_id: {message_id})")

    def _handle_content_event(self, event):
        """Handle events with content."""
        from agent.chat.content import TextContent, ThinkingContent, LlmOutputContent
        from agent.chat.agent_chat_types import ContentType

        sender_id = getattr(event, "sender_id", "")
        if hasattr(event, "agent_name"):
            sender_id = getattr(event, "agent_name", "").lower()

        if sender_id == "user":
            return

        # Check if this content belongs to an active skill
        run_id = getattr(event, "run_id", "")

        # Prepare content dict - handle all content types generically
        content_dict = None

        # If event.content is already a StructureContent, use its to_dict()
        if hasattr(event.content, 'to_dict') and callable(event.content.to_dict):
            content_dict = event.content.to_dict()
        else:
            # For raw content, determine the type and create appropriate StructureContent
            message_type = getattr(event, "message_type", None)
            if message_type == ContentType.THINKING:
                thinking_content = event.content
                if isinstance(thinking_content, str) and thinking_content.startswith("🤔 Thinking: "):
                    thinking_content = thinking_content[len("🤔 Thinking: "):]
                content_dict = ThinkingContent(
                    thought=thinking_content,
                    title="Thinking Process",
                    description="Agent's thought process",
                ).to_dict()
            elif message_type == ContentType.LLM_OUTPUT:
                content_dict = LlmOutputContent(
                    output=event.content if isinstance(event.content, str) else str(event.content),
                    title="LLM Output"
                ).to_dict()
            else:
                # Default to TextContent for all other types
                content_dict = TextContent(text=event.content).to_dict()

        # If there's an active skill, add ALL content to its child_contents
        # This ensures all content during skill lifecycle is merged into the skill
        if run_id and run_id in self._active_skills:
            skill_info = self._active_skills[run_id]
            message_id = skill_info["message_id"]

            # Add to child contents (regardless of content type)
            skill_info["child_contents"].append(content_dict)

            # Update the skill to show the new child content
            # Pass run_id to ensure we only update the matching skill
            self._add_child_to_skill(message_id, content_dict, run_id=run_id)
            return

        # No active skill - handle as standalone content
        item = self._model.get_item_by_message_id(event.message_id)
        if not item:
            agent_name = getattr(event, "agent_name", "Unknown")
            self.get_or_create_agent_card(
                event.message_id,
                agent_name,
                getattr(event, "title", None),
            )

        self.update_agent_card(event.message_id, structured_content=content_dict)

    def _scroll_to_bottom(self, force: bool = False):
        """Scroll the chat list to bottom.

        Args:
            force: If True, scroll regardless of user position.
                   If False, only scroll if user is already at bottom.
        """
        if self._qml_root and (force or self._user_at_bottom):
            # Flush any pending model updates so QML has the latest content
            # before we scroll (ensures correct content height for positioning)
            self._model.flush_updates()
            self._qml_root.scrollToBottom()

    def _get_first_visible_message_id(self) -> Optional[str]:
        """Get the first visible message ID (approximated as first item in model)."""
        if self._model.rowCount() > 0:
            item = self._model.get_item(0)
            if item:
                return item.get(QmlAgentChatListModel.MESSAGE_ID)
        return None

    def _restore_scroll_position(self):
        """Restore scroll position to the previously visible message."""
        if not self._first_visible_message_id_before_load:
            return

        # Always clear the saved message ID, even if qml_root is not available
        saved_message_id = self._first_visible_message_id_before_load
        self._first_visible_message_id_before_load = None

        if not self._qml_root:
            return

        # Find the new index of the message that was at the top
        row = self._model.get_row_by_message_id(saved_message_id)

        if row is not None and row >= 0:
            # Position the view so this message is near the top
            self._qml_root.positionViewAtIndex(row, 1)  # 1 = Beginning
        else:
            # Message not found (might have been pruned), scroll to a reasonable position
            # Use the saved message count from before the load to approximate position
            # The count was saved in _load_older_messages before prepending
            if hasattr(self, '_item_count_before_load') and self._item_count_before_load > 0:
                # Position to where the original first message is now (shifted by new items)
                new_items_count = self._model.rowCount() - self._item_count_before_load
                target_row = min(new_items_count, self._model.rowCount() - 1)
                self._qml_root.positionViewAtIndex(target_row, 1)  # 1 = Beginning
                self._item_count_before_load = 0
            else:
                # Fallback: scroll near the top but not at the very edge
                target_row = min(5, self._model.rowCount() - 1)
                self._qml_root.positionViewAtIndex(target_row, 1)  # 1 = Beginning

    def sync_from_session(self, session):
        """Sync from session."""
        pass

    # ─── New data polling ─────────────────────────────────────────────

    def _start_new_data_check_timer(self):
        """Start the timer to check for new data."""
        self._new_data_check_timer.start(self.NEW_DATA_CHECK_INTERVAL_MS)

    def _stop_new_data_check_timer(self):
        """Stop the new data check timer."""
        self._new_data_check_timer.stop()

    def _check_for_new_data(self):
        """Check for new data by comparing active log count.

        This method is called both by the timer (backup) and by message_saved signal.

        Enhanced with GSN support for archive-aware checking.
        """
        try:
            # Try to use GSN-based checking first
            from agent.chat.history.agent_chat_history_service import FastMessageHistoryService

            current_gsn = FastMessageHistoryService.get_current_gsn(
                self.workspace.workspace_path,
                self.workspace.project_name
            )

            # Check if we have new messages via GSN
            if current_gsn > self._load_state.current_gsn:
                self._load_state.current_gsn = current_gsn
                self._load_new_messages_from_history(current_gsn, current_gsn)
                return

            # Fallback to legacy line-based checking
            history = self._get_history()
            if not history:
                return

            # Use active log count for fast checking (O(1) cached value)
            current_count = history.storage.get_message_count()

            # Check if new messages were added to active log
            if current_count > self._load_state.active_log_count:
                self._load_state.active_log_count = current_count
                self._load_new_messages_from_history()

        except Exception as e:
            logger.error(f"Error checking for new data: {e}")

    def _load_new_messages_from_history(self, trigger_gsn: int = 0, current_gsn: int = 0):
        """Load new messages from history that aren't in the model yet.

        This method handles two scenarios:
        1. New messages (not in model) - creates new bubbles
        2. Existing messages (same message_id) - merges new content into existing bubbles

        For streaming responses that are saved in chunks with the same message_id,
        this method ensures all content chunks are properly merged into the existing
        message bubble instead of being ignored.

        Enhanced with GSN (Global Sequence Number) support for archive-aware
        message fetching. When GSN parameters are provided, uses GSN-based fetching
        which correctly handles archived messages.

        Args:
            trigger_gsn: The GSN that triggered this load (optional)
            current_gsn: The current (latest) GSN in the system (optional)
        """
        try:
            use_gsn_fetching = trigger_gsn > 0 or current_gsn > 0

            if use_gsn_fetching:
                # Use GSN-based fetching (archive-aware)
                new_messages = self._fetch_messages_by_gsn(trigger_gsn, current_gsn)
            else:
                # Legacy line-offset-based fetching
                history = self._get_history()
                if not history:
                    return

                # Get messages after current offset
                current_offset = self._load_state.current_line_offset
                new_messages = history.get_messages_after(current_offset, count=100)

            if not new_messages:
                return

            # Group messages by message_id (don't skip known ones yet)
            # We need to collect all messages including ones for existing bubbles
            message_groups: Dict[str, MessageGroup] = {}
            for msg_data in new_messages:
                message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
                if not message_id:
                    continue

                # Always add to groups for processing
                if message_id not in message_groups:
                    message_groups[message_id] = MessageGroup()
                message_groups[message_id].add_message(msg_data)

            # Process messages - handle both new and existing message_ids
            for message_id, group in message_groups.items():
                combined_msg = group.get_combined_message()
                if not combined_msg:
                    continue

                # Check if this message already exists in the model
                existing_row = self._model.get_row_by_message_id(message_id)

                if existing_row is not None:
                    # Message bubble already exists - merge new content
                    self._merge_content_into_existing_bubble(message_id, combined_msg)
                    logger.debug(f"Merged new content into existing bubble: {message_id[:8]}...")
                else:
                    # New message - create new bubble
                    item = self._build_item_from_history(combined_msg)
                    if item:
                        qml_item = QmlAgentChatListModel.from_chat_list_item(item)
                        self._model.add_item(qml_item)
                        self._load_state.known_message_ids.add(message_id)

            # Update tracking
            if not use_gsn_fetching:
                # Legacy offset tracking
                if new_messages:
                    current_offset = self._load_state.current_line_offset
                    self._load_state.current_line_offset = current_offset + len(new_messages)
            else:
                # GSN tracking
                self._load_state.last_seen_gsn = current_gsn

            # Update unique message count
            if new_messages:
                # Only count unique new messages (not updates to existing ones)
                new_unique_count = sum(1 for msg_id in message_groups.keys()
                                      if msg_id not in self._load_state.known_message_ids)
                self._load_state.unique_message_count += new_unique_count
                # Add all processed message_ids to known set
                for msg_id in message_groups.keys():
                    self._load_state.known_message_ids.add(msg_id)

                # Scroll to bottom only if user is already there (don't interrupt reading history)
                self._scroll_to_bottom(force=False)
                fetch_method = "GSN" if use_gsn_fetching else "line-offset"
                logger.debug(f"Processed {len(message_groups)} message groups from history using {fetch_method} fetching")

        except Exception as e:
            logger.error(f"Error loading new messages from history: {e}", exc_info=True)

    def _fetch_messages_by_gsn(self, trigger_gsn: int, current_gsn: int) -> List[Dict[str, Any]]:
        """Fetch messages using GSN-based (archive-aware) method.

        Args:
            trigger_gsn: The GSN that triggered this fetch
            current_gsn: The current (latest) GSN

        Returns:
            List of message dictionaries
        """
        try:
            from agent.chat.history.agent_chat_history_service import FastMessageHistoryService

            # Get messages after the last seen GSN
            last_seen = self._load_state.last_seen_gsn
            new_messages = FastMessageHistoryService.get_messages_after_gsn(
                self.workspace.workspace_path,
                self.workspace.project_name,
                last_seen_gsn=last_seen,
                count=100
            )

            logger.debug(f"GSN fetch: last_seen={last_seen}, current={current_gsn}, found={len(new_messages)} messages")
            return new_messages

        except Exception as e:
            logger.error(f"Error in GSN-based fetching: {e}")
            # Fallback to legacy method
            return []

    def _merge_content_into_existing_bubble(self, message_id: str, combined_msg: Dict[str, Any]) -> None:
        """Merge new content into an existing message bubble.

        Args:
            message_id: The ID of the message to update
            combined_msg: The combined message data with new content
        """
        try:
            # Build item from the combined message to get structured content
            item = self._build_item_from_history(combined_msg)
            if not item:
                return

            # Convert to QML format to extract structured content
            qml_item = QmlAgentChatListModel.from_chat_list_item(item)
            new_structured_content = qml_item.get(QmlAgentChatListModel.STRUCTURED_CONTENT, [])

            if not new_structured_content:
                return

            # Get current item from model
            existing_row = self._model.get_row_by_message_id(message_id)
            if existing_row is None:
                return

            current_item = self._model.get_item(existing_row)
            if not current_item:
                return

            # Get existing structured content
            current_structured = current_item.get(QmlAgentChatListModel.STRUCTURED_CONTENT, [])

            # Merge content items - add new items that aren't already present
            merged_content = list(current_structured)

            # Track existing content types to avoid duplicates
            # For streaming text, we want to append; for other types, we might want to replace
            for new_content in new_structured_content:
                content_type = new_content.get('content_type', '')

                # Special handling for text content - always append (streaming)
                if content_type == 'text':
                    merged_content.append(new_content)
                # For other content types, check if we should replace or append
                elif content_type == 'thinking':
                    # Replace existing thinking content with new one
                    merged_content = [c for c in merged_content
                                    if c.get('content_type') != 'thinking']
                    merged_content.append(new_content)
                elif content_type == 'typing':
                    # Remove old typing indicators before adding new one
                    merged_content = [c for c in merged_content
                                    if c.get('content_type') != 'typing']
                    merged_content.append(new_content)
                else:
                    # For other types (progress, tool_call, etc.), append if not duplicate
                    # Simple check: compare string representation
                    new_str = str(new_content)
                    if not any(str(c) == new_str for c in merged_content):
                        merged_content.append(new_content)

            # Update the model with merged content
            self._model.update_item(message_id, {
                QmlAgentChatListModel.STRUCTURED_CONTENT: merged_content
            })

            # Also update the plain text content if needed
            # Extract text from the new content and append
            new_text = qml_item.get(QmlAgentChatListModel.CONTENT, "")
            if new_text:
                current_text = current_item.get(QmlAgentChatListModel.CONTENT, "")
                # Only append if the new text adds something meaningful
                if new_text not in current_text:
                    updated_text = current_text + new_text if current_text else new_text
                    self._model.update_item(message_id, {
                        QmlAgentChatListModel.CONTENT: updated_text
                    })

            logger.debug(f"Merged {len(new_structured_content)} content items into {message_id[:8]}...")

        except Exception as e:
            logger.error(f"Error merging content for {message_id[:8]}...: {e}", exc_info=True)

    def clear(self):
        """Clear the chat list."""
        self._stop_new_data_check_timer()
        self._disconnect_from_storage_signals()
        self._model.clear()
        self._agent_current_cards.clear()
        self._load_state = LoadState()
        self._loading_older = False
        # Don't restart timer - rely on message_saved signal instead
