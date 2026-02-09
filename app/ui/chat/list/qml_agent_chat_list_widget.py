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
from agent.chat.agent_chat_types import MessageType, ContentType
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
    PAGE_SIZE = 30
    MAX_MODEL_ITEMS = 300
    NEW_DATA_CHECK_INTERVAL_MS = 500
    SCROLL_TOP_THRESHOLD = 50

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

        # State tracking
        self._load_state = LoadState()
        self._loading_older = False
        self._user_at_bottom = True

        # Crew member metadata cache
        self._crew_member_metadata: Dict[str, Dict[str, Any]] = {}
        self._agent_current_cards: Dict[str, str] = {}

        # History cache
        self._history: Optional[MessageLogHistory] = None

        # New data check timer - polls for new messages using active log count
        # NOTE: This is kept as backup but primary loading is driven by message_saved signal
        self._new_data_check_timer = QTimer(self)
        self._new_data_check_timer.timeout.connect(self._check_for_new_data)

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
        """Handle load more request from QML (scroll to top)."""
        if not self._loading_older and self._load_state.has_more_older:
            self._load_older_messages()

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

    def _on_message_saved(self, sender, workspace_path: str, project_name: str, message_id: str):
        """Handle message_saved signal from storage.

        This is called after a message is successfully written to storage.
        We trigger a data refresh to load the new message from storage.
        """
        # Only refresh if this message belongs to our current project
        if (workspace_path == self.workspace.workspace_path and
            project_name == self.workspace.project_name):
            # Load new messages from storage
            # Unlike the polling version, we always attempt to load (no _user_at_bottom check)
            # This ensures messages are loaded even when user is viewing history
            self._load_new_messages_from_history()

    def _clear_all_caches_and_model(self):
        """Clear all caches and the model."""
        self._model.clear()
        self._load_state.known_message_ids.clear()
        self._load_state.unique_message_count = 0
        self._load_state.has_more_older = False

    def _load_recent_conversation(self):
        """Load recent conversation from history."""
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

            if raw_messages:
                self._clear_all_caches_and_model()

                # Group messages by message_id
                message_groups: Dict[str, MessageGroup] = {}
                for msg_data in raw_messages:
                    message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
                    if not message_id:
                        continue

                    if message_id not in message_groups:
                        message_groups[message_id] = MessageGroup()
                    message_groups[message_id].add_message(msg_data)

                # Convert to ordered list
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
                self._load_state.has_more_older = len(raw_messages) >= self.PAGE_SIZE

                total_count = history.get_total_count()
                logger.info(f"Loaded {len(ordered_messages)} unique messages (total: {total_count})")

                # Force QML to update model binding
                self._refresh_qml_model()

                # Scroll to bottom after loading
                self._scroll_to_bottom()

            else:
                self._clear_all_caches_and_model()
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
            history = self._get_history()
            if not history:
                return

            current_offset = self._load_state.current_line_offset
            older_messages = history.get_messages_before(current_offset, count=self.PAGE_SIZE)

            if not older_messages:
                self._load_state.has_more_older = False
                return

            # Group and build items
            message_groups: Dict[str, MessageGroup] = {}
            for msg_data in older_messages:
                message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
                if not message_id:
                    continue

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
                # Convert to QML format and prepend
                qml_items = [QmlAgentChatListModel.from_chat_list_item(item) for item in items]
                self._model.prepend_items(qml_items)

                self._load_state.unique_message_count += len(items)
                self._load_state.current_line_offset = current_offset - len(older_messages)

                self._prune_model_bottom()
                logger.debug(f"Prepended {len(items)} older messages")

            if len(older_messages) < self.PAGE_SIZE:
                self._load_state.has_more_older = False

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
            message_type_str = msg_data.get("message_type") or metadata.get("message_type", "text")
            timestamp = msg_data.get("timestamp") or metadata.get("timestamp")

            if not message_id:
                logger.warning(f"No message_id in msg_data: {msg_data.keys()}")
                return None

            logger.debug(f"Parsing message: {message_id[:8]}... from {sender_name}")

            try:
                message_type = MessageType(message_type_str)
            except ValueError:
                message_type = MessageType.TEXT

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
                # Skip system messages that are just metadata
                if message_type == MessageType.SYSTEM:
                    event_type = metadata.get("event_type", "")
                    if event_type in ("producer_start", "crew_member_start", "responding_agent_start"):
                        logger.debug(f"  Skipping system event: {event_type}")
                        return None

                structured_content = []
                for content_item in content_list:
                    if isinstance(content_item, dict):
                        try:
                            sc = StructureContent.from_dict(content_item)
                            structured_content.append(sc)
                        except Exception as e:
                            logger.debug(f"Failed to load structured content: {e}")

                # Add timestamp to metadata for QML
                if timestamp and "timestamp" not in metadata:
                    metadata["timestamp"] = timestamp

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
        self._scroll_to_bottom()
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
        self._scroll_to_bottom()
        return message_id

    def update_streaming_message(self, message_id: str, content: str):
        """Update a streaming message."""
        self._model.update_item(message_id, {
            QmlAgentChatListModel.CONTENT: content,
        })
        self._scroll_to_bottom()

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
        self._scroll_to_bottom()
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

        self._scroll_to_bottom()

    @Slot(object, object)
    def handle_stream_event(self, event, session):
        """Handle stream events."""
        if event.event_type == "error":
            self._handle_error_event(event)
        elif event.event_type == "agent_response":
            self._handle_agent_response_event(event)
        elif event.event_type in ["skill_start", "skill_progress", "skill_end"]:
            self._handle_skill_event(event)
        elif event.event_type in ["crew_member_typing", "crew_member_typing_end"]:
            self._handle_typing_event(event)
        elif hasattr(event, "content") and event.content:
            self._handle_content_event(event)

    def _handle_error_event(self, event):
        """Handle error events."""
        from agent.chat.content import ErrorContent

        error_content = event.data.get("content", "Unknown error")
        message_id = str(uuid.uuid4())
        self.get_or_create_agent_card(message_id, "System", "System")

        error_structure = ErrorContent(error_message=error_content)
        self.update_agent_card(
            message_id,
            structured_content=error_structure,
            error=error_content,
        )

    def _handle_agent_response_event(self, event):
        """Handle agent response events."""
        from agent.chat.content import TextContent

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

    def _handle_skill_event(self, event):
        """Handle skill events."""
        from agent.chat.content import ProgressContent

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
        from agent.chat.content import TextContent, ThinkingContent

        sender_id = getattr(event, "sender_id", "")
        if hasattr(event, "agent_name"):
            sender_id = getattr(event, "agent_name", "").lower()

        if sender_id == "user":
            return

        message_type = getattr(event, "message_type", None)
        item = self._model.get_item_by_message_id(event.message_id)
        if not item:
            agent_name = getattr(event, "agent_name", "Unknown")
            self.get_or_create_agent_card(
                event.message_id,
                agent_name,
                getattr(event, "title", None),
            )

        if message_type == MessageType.THINKING:
            if isinstance(event.content, ThinkingContent):
                thinking_structure = event.content.to_dict()
            else:
                thinking_content = event.content
                if thinking_content.startswith("🤔 Thinking: "):
                    thinking_content = thinking_content[len("🤔 Thinking: "):]
                thinking_structure = ThinkingContent(
                    thought=thinking_content,
                    title="Thinking Process",
                    description="Agent's thought process",
                ).to_dict()
            self.update_agent_card(event.message_id, structured_content=thinking_structure)
        else:
            text_structure = TextContent(text=event.content).to_dict()
            self.update_agent_card(event.message_id, structured_content=text_structure)

    def _scroll_to_bottom(self):
        """Scroll the chat list to bottom."""
        if self._qml_root:
            self._qml_root.scrollToBottom()

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
        """
        try:
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

    def _load_new_messages_from_history(self):
        """Load new messages from history that aren't in the model yet.

        This method handles two scenarios:
        1. New messages (not in model) - creates new bubbles
        2. Existing messages (same message_id) - merges new content into existing bubbles

        For streaming responses that are saved in chunks with the same message_id,
        this method ensures all content chunks are properly merged into the existing
        message bubble instead of being ignored.
        """
        try:
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
                        logger.debug(f"Created new bubble: {message_id[:8]}...")

            # Update offset
            if new_messages:
                self._load_state.current_line_offset = current_offset + len(new_messages)
                # Only count unique new messages (not updates to existing ones)
                new_unique_count = sum(1 for msg_id in message_groups.keys()
                                      if msg_id not in self._load_state.known_message_ids)
                self._load_state.unique_message_count += new_unique_count
                # Add all processed message_ids to known set
                for msg_id in message_groups.keys():
                    self._load_state.known_message_ids.add(msg_id)

                # Scroll to bottom to show new messages
                self._scroll_to_bottom()
                logger.debug(f"Processed {len(message_groups)} message groups from history")

        except Exception as e:
            logger.error(f"Error loading new messages from history: {e}", exc_info=True)

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
