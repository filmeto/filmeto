"""QML-based AgentChatListWidget with Qt Quick Controls 2.

This module provides a complete rewrite of the agent chat list using QML + Qt Quick,
offering superior performance with dynamic heights, smooth scrolling, and 60 FPS rendering.

This is the refactored version that uses composition with multiple focused components
instead of a monolithic class.
"""

import logging
import uuid
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import QUrl, Slot, Signal, QTimer
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QWidget, QVBoxLayout

from agent.chat.content import StructureContent
from agent.chat.history.agent_chat_history_service import message_saved
from app.ui.base_widget import BaseWidget
from app.ui.chat.list.agent_chat_list_items import ChatListItem
from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.managers.history_manager import HistoryManager
from app.ui.chat.list.managers.metadata_resolver import MetadataResolver
from app.ui.chat.list.managers.scroll_manager import ScrollManager
from app.ui.chat.list.managers.skill_manager import SkillManager
from app.ui.chat.list.builders.message_builder import MessageBuilder
from app.ui.chat.list.handlers.qml_handler import QmlHandler
from app.ui.chat.list.handlers.stream_event_handler import StreamEventHandler
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.data.workspace import Workspace


class QmlAgentChatListWidget(BaseWidget):
    """QML-based chat list widget with hardware-accelerated rendering.

    This refactored version uses composition with focused components:
    - HistoryManager: Handles loading messages from storage
    - SkillManager: Manages skill lifecycle and content merging
    - MetadataResolver: Resolves crew member metadata
    - ScrollManager: Manages scroll position
    - MessageBuilder: Builds message items from history
    - QmlHandler: Handles QML signal connections and interactions
    - StreamEventHandler: Routes stream events to appropriate handlers

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

    # Configuration constants
    PAGE_SIZE = 200
    MAX_MODEL_ITEMS = 300
    LOAD_MORE_DEBOUNCE_MS = 300

    # Signals
    reference_clicked = Signal(str, str)  # ref_type, ref_id
    message_complete = Signal(str, str)  # message_id, agent_name
    load_more_requested = Signal()

    def __init__(self, workspace: "Workspace", parent=None):
        """Initialize the chat list widget.

        Args:
            workspace: Workspace instance
            parent: Parent widget
        """
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        # Initialize QML Model
        self._model = QmlAgentChatListModel(self)

        # Initialize QML View widget
        self._quick_widget = QQuickWidget(self)
        self._quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)

        # Register context property for model access (matches _chatModel in QML)
        self._quick_widget.rootContext().setContextProperty("_chatModel", self._model)

        # Get correct QML path (qml is in app/ui/qml, widget is in app/ui/chat/list)
        qml_path = Path(__file__).parent.parent.parent / "qml" / "chat" / "AgentChatList.qml"
        if not qml_path.exists():
            logger.error(f"QML file not found at: {qml_path}")
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

        # Initialize components
        self._initialize_components()

        # Setup UI and load data
        self._setup_ui()
        self._metadata_resolver.load_crew_member_metadata()
        self._history_manager.load_recent_conversation()

    def _initialize_components(self) -> None:
        """Initialize all component managers and handlers."""
        # Create MetadataResolver first (others depend on it)
        self._metadata_resolver = MetadataResolver(self.workspace)

        # Create MessageBuilder
        self._message_builder = MessageBuilder(self._metadata_resolver, self._model)

        # Create ScrollManager
        self._scroll_manager = ScrollManager(self._model, self.LOAD_MORE_DEBOUNCE_MS)

        # Create SkillManager
        self._skill_manager = SkillManager(
            self._model,
            self._metadata_resolver,
            self._scroll_manager,
        )

        # Create HistoryManager
        self._history_manager = HistoryManager(
            self.workspace,
            self._model,
            self._message_builder,
        )

        # Create QmlHandler
        self._qml_handler = QmlHandler(self._model, self.LOAD_MORE_DEBOUNCE_MS)
        self._qml_handler.set_qml_root(self._qml_root)

        # Create StreamEventHandler
        self._stream_event_handler = StreamEventHandler(
            self._model,
            self._skill_manager,
            self._metadata_resolver,
        )

        # Set up callbacks between components
        self._setup_component_callbacks()

        # Connect to storage signals
        self._history_manager.connect_to_storage_signals()

    def _setup_component_callbacks(self) -> None:
        """Set up callbacks between components."""
        # Load more debounce timer
        load_more_timer = QTimer(self)
        load_more_timer.setSingleShot(True)
        load_more_timer.timeout.connect(self._history_manager.load_older_messages)
        self._scroll_manager.set_qml_root(self._qml_root)
        self._scroll_manager.connect_load_more_callback(self._history_manager.load_older_messages)
        self._qml_handler.set_debounce_timer(load_more_timer)

        # QmlHandler callbacks
        self._qml_handler.set_callbacks(
            on_reference_clicked=lambda ref_type, ref_id: self.reference_clicked.emit(ref_type, ref_id),
            on_message_completed=lambda msg_id, agent_name: self.message_complete.emit(msg_id, agent_name),
            on_load_more=lambda: self.load_more_requested.emit(),
        )

        # StreamEventHandler callbacks
        self._stream_event_handler.set_callbacks(
            update_agent_card=self._update_agent_card_internal,
            scroll_to_bottom=self._scroll_to_bottom,
        )

        # HistoryManager callbacks
        self._history_manager.set_qml_root(self._qml_root)
        self._history_manager.set_callbacks(
            on_load_more=lambda: self.load_more_requested.emit(),
            refresh_qml=self._refresh_qml_model,
            scroll_to_bottom=self._scroll_to_bottom,
            get_first_visible_message_id=self._qml_handler.get_first_visible_message_id,
            restore_scroll_position=self._qml_handler.restore_scroll_position,
        )

    def _setup_ui(self) -> None:
        """Setup the widget layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)
        layout.addWidget(self._quick_widget)

    def _refresh_qml_model(self) -> None:
        """Force QML to refresh the model binding."""
        self._qml_handler.refresh_model_binding(self._quick_widget)

    def _scroll_to_bottom(self, force: bool = False) -> None:
        """Scroll the chat list to bottom.

        Args:
            force: If True, scroll regardless of user position.
        """
        self._scroll_manager.scroll_to_bottom(force=force)

    def _update_agent_card_internal(
        self,
        message_id: str,
        content: str = None,
        append: bool = True,
        is_thinking: bool = False,
        thinking_text: str = "",
        is_complete: bool = False,
        structured_content=None,
        error: str = None,
    ) -> None:
        """Internal method to update an agent message card.

        Args:
            message_id: The message ID to update
            content: Text content to update
            append: Whether to append to existing content
            is_thinking: Whether this is a thinking indicator
            thinking_text: Thinking text content
            is_complete: Whether the message is complete
            structured_content: Structured content to add
            error: Error message
        """
        updates = {}

        # Update content
        if content is not None:
            item = self._model.get_item(self._model.get_row_by_message_id(message_id) or 0)
            if item:
                current_content = item.get(self._model.CONTENT, "")
                new_content = (current_content + content) if append else content
                updates[self._model.CONTENT] = new_content

        # Update structured content
        if structured_content is not None:
            item = self._model.get_item(self._model.get_row_by_message_id(message_id) or 0)
            if item:
                current_structured = item.get(self._model.STRUCTURED_CONTENT, [])

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
                updates[self._model.STRUCTURED_CONTENT] = new_structured

                # Update content type based on structured content
                if items:
                    primary_type = items[0].get('content_type', 'text')
                    updates[self._model.CONTENT_TYPE] = primary_type

        # Handle error
        if error:
            error_text = f"❌ Error: {error}"
            updates[self._model.CONTENT] = error_text
            updates[self._model.CONTENT_TYPE] = "error"

        if updates:
            self._model.update_item(message_id, updates)

        self._scroll_to_bottom(force=True)

    # ─── Public API ───────────────────────────────────────────────────────

    def add_user_message(self, content: str) -> str:
        """Add a user message to the chat.

        Args:
            content: The message content

        Returns:
            The message ID
        """
        message_id = str(uuid.uuid4())

        item = {
            self._model.MESSAGE_ID: message_id,
            self._model.SENDER_ID: "user",
            self._model.SENDER_NAME: tr("User"),
            self._model.IS_USER: True,
            self._model.CONTENT: content,
            self._model.AGENT_COLOR: "#4a90e2",
            self._model.AGENT_ICON: "\ue6b3",
            self._model.CREW_METADATA: {},
            self._model.STRUCTURED_CONTENT: [],
            self._model.CONTENT_TYPE: "text",
            self._model.IS_READ: True,
            self._model.TIMESTAMP: None,
            self._model.DATE_GROUP: "",
        }

        self._model.add_item(item)
        self._scroll_to_bottom(force=True)
        return message_id

    def append_message(self, sender: str, message: str, message_id: str = None) -> Optional[str]:
        """Append a message to the chat.

        Args:
            sender: The sender name/ID
            message: The message content
            message_id: Optional message ID

        Returns:
            The message ID or None
        """
        if not message:
            return None

        is_user = sender.lower() in ["user", tr("用户").lower(), tr("user").lower()]
        if is_user:
            return self.add_user_message(message)

        if not message_id:
            message_id = str(uuid.uuid4())

        agent_color, agent_icon, crew_member_data = self._metadata_resolver.resolve_agent_metadata(sender)

        item = {
            self._model.MESSAGE_ID: message_id,
            self._model.SENDER_ID: sender,
            self._model.SENDER_NAME: sender,
            self._model.IS_USER: False,
            self._model.CONTENT: message,
            self._model.AGENT_COLOR: agent_color,
            self._model.AGENT_ICON: agent_icon,
            self._model.CREW_METADATA: crew_member_data,
            self._model.STRUCTURED_CONTENT: [],
            self._model.CONTENT_TYPE: "text",
            self._model.IS_READ: True,
            self._model.TIMESTAMP: None,
            self._model.DATE_GROUP: "",
        }

        self._model.add_item(item)
        self._scroll_to_bottom(force=True)
        return message_id

    def update_streaming_message(self, message_id: str, content: str) -> None:
        """Update a streaming message.

        Args:
            message_id: The message ID to update
            content: The new content
        """
        self._model.update_item(message_id, {
            self._model.CONTENT: content,
        })
        self._scroll_to_bottom(force=True)

    def get_or_create_agent_card(
        self,
        message_id: str,
        agent_name: str,
        title=None
    ) -> str:
        """Get or create an agent message card.

        Args:
            message_id: The message ID
            agent_name: The agent name
            title: Optional title

        Returns:
            The message ID
        """
        return self._skill_manager.get_or_create_agent_card(message_id, agent_name, title)

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
    ) -> None:
        """Update an agent message card.

        Args:
            message_id: The message ID to update
            content: Text content to update
            append: Whether to append to existing content
            is_thinking: Whether this is a thinking indicator
            thinking_text: Thinking text content
            is_complete: Whether the message is complete
            structured_content: Structured content to add
            error: Error message
        """
        self._update_agent_card_internal(
            message_id,
            content=content,
            append=append,
            is_thinking=is_thinking,
            thinking_text=thinking_text,
            is_complete=is_complete,
            structured_content=structured_content,
            error=error,
        )

    @Slot(object, object)
    def handle_stream_event(self, event, session) -> None:
        """Handle stream events.

        Args:
            event: The stream event
            session: The session context
        """
        self._stream_event_handler.handle_stream_event(event, session)

    def on_project_switched(self, project_name: str) -> None:
        """Handle project switch.

        Args:
            project_name: The new project name
        """
        self._metadata_resolver.load_crew_member_metadata()
        self._history_manager.on_project_switched()

    def refresh_crew_member_metadata(self) -> None:
        """Reload crew member metadata."""
        self._metadata_resolver.load_crew_member_metadata()

    def sync_from_session(self, session) -> None:
        """Sync from session.

        Args:
            session: The session context
        """
        pass

    def clear(self) -> None:
        """Clear the chat list."""
        self._history_manager.disconnect_from_storage_signals()
        self._model.clear()
        self._skill_manager.clear()
        self._history_manager.clear_all_caches_and_model()
