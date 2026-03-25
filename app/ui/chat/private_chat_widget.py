"""Private chat widget for 1-on-1 conversations with a crew member.

This widget provides a dedicated chat interface for direct messaging
with an individual crew member, using their chat_stream interface.
Messages are stored in the crew member's own history and do NOT
leak into the group chat.

Real-time rendering:
- User-initiated messages: rendered via streaming (handle_stream_event)
- System-routed messages: rendered via crew_member_message_saved signal
"""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Dict, Any

from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtCore import Qt, Signal, QTimer, QObject, Property, Slot, QUrl
from PySide6.QtQuickWidgets import QQuickWidget

from agent.crew import CrewMember
from agent.crew.crew_member_history_service import crew_member_message_saved
from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.builders.message_builder import MessageBuilder
from app.ui.chat.list.builders.message_converter import MessageConverter
from app.ui.chat.list.handlers.qml_handler import QmlHandler
from app.ui.chat.list.handlers.stream_event_handler import StreamEventHandler
from app.ui.chat.list.managers.metadata_resolver import MetadataResolver
from app.ui.chat.list.managers.scroll_manager import ScrollManager
from app.ui.chat.list.managers.skill_manager import SkillManager
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)
PRIVATE_VIEW_QML_PATH = Path(__file__).parent.parent / "qml" / "chat" / "widgets" / "PrivateChatView.qml"


class _ChatInputBridge(QObject):
    textChanged = Signal()
    enabledChanged = Signal()
    placeholderChanged = Signal()
    sendLabelChanged = Signal()
    submitted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self._enabled = True
        self._placeholder = tr("Type your message...")
        self._send_label = tr("Send")

    @Property(str, notify=textChanged)
    def text(self) -> str:
        return self._text

    @Property(bool, notify=enabledChanged)
    def enabled(self) -> bool:
        return self._enabled

    @Property(str, notify=placeholderChanged)
    def placeholder(self) -> str:
        return self._placeholder

    @Property(str, notify=sendLabelChanged)
    def sendLabel(self) -> str:
        return self._send_label

    @Slot(str)
    def on_text_changed(self, value: str):
        if self._text != value:
            self._text = value
            self.textChanged.emit()

    @Slot()
    def submit(self):
        message = (self._text or "").strip()
        if not message or not self._enabled:
            return
        self.submitted.emit(message)
        self._text = ""
        self.textChanged.emit()

    def set_enabled(self, enabled: bool):
        if self._enabled != enabled:
            self._enabled = enabled
            self.enabledChanged.emit()


class PrivateChatWidget(BaseWidget):
    """Chat widget for private 1-on-1 conversation with a crew member."""

    error_occurred = Signal(str)
    # Internal signal to marshal blinker callback onto the Qt main thread
    _new_history_message = Signal(dict)
    # Signal emitted when tab becomes active/inactive
    active_changed = Signal(bool)

    def __init__(self, workspace: Workspace, crew_member: CrewMember, parent=None):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        self.crew_member = crew_member
        self._is_processing = False
        self._is_active = False  # Track if this tab is currently active
        self._history_loaded = False  # Track if initial history has been loaded
        self._last_rendered_offset = 0  # Track last rendered message offset for incremental loading

        # QML + model/controller state
        self._model: QmlAgentChatListModel | None = None
        self._metadata_resolver: MetadataResolver | None = None
        self._message_builder: MessageBuilder | None = None
        self._qml_handler: QmlHandler | None = None
        self._scroll_manager: ScrollManager | None = None
        self._skill_manager: SkillManager | None = None
        self._stream_event_handler: StreamEventHandler | None = None
        self._qml_root = None
        self._chat_list_qml = None

        self.error_occurred.connect(self._on_error)
        self._new_history_message.connect(self._render_history_message)
        self._input_bridge = _ChatInputBridge(self)
        self._setup_ui()
        self._connect_history_signal()

        QTimer.singleShot(200, self._load_history)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._init_private_chat_controller()

        self._quick = QQuickWidget(self)
        self._quick.setObjectName("private_chat_qml")
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick.setAttribute(Qt.WA_TranslucentBackground, True)
        self._quick.setClearColor(Qt.transparent)

        qml_root_dir = Path(__file__).resolve().parent.parent / "qml"
        self._quick.engine().addImportPath(str(qml_root_dir))

        # Expose legacy name for AgentChatList.qml fallback.
        self._quick.rootContext().setContextProperty("_chatModel", self._model)
        self._quick.rootContext().setContextProperty("inputBridge", self._input_bridge)

        self._quick.statusChanged.connect(self._on_prompt_qml_status_changed)
        self._quick.setSource(QUrl.fromLocalFile(str(PRIVATE_VIEW_QML_PATH)))
        self._check_prompt_qml_loaded()

        self._qml_root = self._quick.rootObject()
        if self._qml_root is not None:
            self._qml_root.setProperty("chatModel", self._model)
            self._qml_root.setProperty("inputBridge", self._input_bridge)
            self._qml_root.setProperty("title", self.crew_member.config.name)

        self._wire_private_qml()
        layout.addWidget(self._quick)

        self._input_bridge.submitted.connect(self._on_message_submitted)

    def _init_private_chat_controller(self) -> None:
        self._model = QmlAgentChatListModel(self)
        self._metadata_resolver = MetadataResolver(self.workspace)
        self._message_builder = MessageBuilder(self._metadata_resolver, self._model)
        self._qml_handler = QmlHandler(self._model, 300)
        self._scroll_manager = ScrollManager(self._model, 300)
        self._skill_manager = SkillManager(self._model, self._metadata_resolver, self._scroll_manager)
        self._stream_event_handler = StreamEventHandler(self._model, self._skill_manager, self._metadata_resolver)
        self._stream_event_handler.set_callbacks(
            update_agent_card=self._update_agent_card_internal,
            scroll_to_bottom=lambda force=False: self._scroll_manager.scroll_to_bottom(force=force),
            crew_member_activity=lambda _name, _active: None,
        )

    def _wire_private_qml(self) -> None:
        if not self._qml_root:
            return

        try:
            self._chat_list_qml = self._qml_root.findChild(QObject, "privateChatList")
        except Exception:
            self._chat_list_qml = None

        if not self._chat_list_qml:
            logger.error("PrivateChatView missing privateChatList object")
            return

        self._qml_handler.set_qml_root(self._chat_list_qml)
        self._scroll_manager.set_qml_root(self._chat_list_qml)
        self._scroll_manager.set_qml_handler(self._qml_handler)
        self._metadata_resolver.load_crew_member_metadata()

    def _load_history(self):
        """Load the crew member's chat history into the display."""
        try:
            if not self._model:
                self._history_loaded = True
                return
            self._model.clear()

            messages = self.crew_member.get_history_latest(100)
            if not messages:
                self._sync_last_rendered_offset()
                self._history_loaded = True
                return

            # Reverse message order (newest at bottom)
            messages.reverse()

            # Use MessageBuilder for batch building
            items = self._message_builder.build_items_from_raw_messages(messages)

            # Convert to QML format and batch add
            qml_items = [MessageConverter.from_chat_list_item(item) for item in items]
            self._model.add_items_batch(qml_items)

            self._sync_last_rendered_offset()
            self._history_loaded = True

        except Exception as e:
            logger.error(f"Error loading private chat history: {e}", exc_info=True)
            self._history_loaded = True

    # ------------------------------------------------------------------
    # Real-time rendering for system-routed messages
    # ------------------------------------------------------------------

    def _connect_history_signal(self):
        """Listen for new messages written to this crew member's private history."""
        crew_member_message_saved.connect(self._on_crew_member_message_saved, weak=False)

    def _disconnect_history_signal(self):
        try:
            crew_member_message_saved.disconnect(self._on_crew_member_message_saved)
        except Exception:
            pass

    def _on_crew_member_message_saved(
        self,
        sender,
        workspace_path: str,
        project_name: str,
        crew_title: str,
        message: Dict[str, Any],
    ):
        """Blinker callback — may be called from any thread.

        Filters for this crew member and forwards to the Qt main thread
        via the _new_history_message signal.

        Only renders if the tab is active; otherwise messages will be
        loaded incrementally when the tab becomes active.
        """
        if self._is_processing:
            return
        if crew_title != self.crew_member.crew_title:
            return
        if workspace_path != getattr(self.workspace, "workspace_path", None):
            return
        # Only render if tab is active; inactive tabs will load incrementally on activation
        if not self._is_active:
            return
        # Emit with update_offset flag for real-time rendering
        self._new_history_message.emit({"message": message, "update_offset": True})

    def _render_history_message(self, data: dict):
        """Render a single history message on the Qt main thread.

        Args:
            data: Either a message dict directly, or a dict with 'message' and 'update_offset' keys.
                  When called from signal, it's {'message': msg, 'update_offset': bool}.
                  When called directly (e.g., from incremental loading), it's just the message.
        """
        # Handle both formats: direct message or wrapped with update_offset flag
        if "message" in data:
            msg = data["message"]
            update_offset = data.get("update_offset", False)
        else:
            msg = data
            update_offset = False

        self._render_message(msg)

        # Track rendered message count for incremental loading (real-time only)
        if update_offset:
            self._last_rendered_offset += 1

    def _render_message(self, msg: dict):
        """Render a message based on its content structure.

        Uses MessageBuilder for consistent rendering with group chat.
        User messages are handled separately with add_user_message.
        For agent messages with the same message_id (streaming chunks),
        merges into the existing card instead of creating duplicates.

        Args:
            msg: The message dictionary to render
        """
        sender_id = msg.get("sender_id", "")
        content = msg.get("content", "")
        sender_name = msg.get("sender_name", "")
        message_id = msg.get("message_id", str(uuid.uuid4()))
        timestamp = msg.get("timestamp", None)

        if content is None or content == "":
            return

        # User messages special handling
        if sender_id and sender_id.lower() == "user":
            user_text = self._extract_user_text(content)
            self._add_user_message(user_text, timestamp=timestamp)
            return

        # Normalize content to list (history may store single content as dict)
        if isinstance(content, dict):
            msg = {**msg, "content": [content]}
        elif not isinstance(content, list):
            msg = {**msg, "content": []}

        model = self._model
        if not model:
            return
        existing_row = model.get_row_by_message_id(message_id)
        if existing_row is not None:
            self._message_builder.merge_content_into_existing_bubble(message_id, msg)
            return

        item = self._message_builder.build_item_from_history(msg)
        if item:
            qml_item = MessageConverter.from_chat_list_item(item)
            model.add_item(qml_item)

    def _add_user_message(self, content: str, timestamp: str = None) -> None:
        if not self._model:
            return
        message_id = str(uuid.uuid4())
        start_time = QmlAgentChatListModel._format_start_time(timestamp) if timestamp else ""
        date_group = QmlAgentChatListModel._get_date_group(timestamp) if timestamp else ""
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
            self._model.CREW_READ_BY: [],
            self._model.TIMESTAMP: timestamp,
            self._model.START_TIME: start_time,
            self._model.DATE_GROUP: date_group,
        }
        self._model.add_item(item)
        if self._scroll_manager:
            self._scroll_manager.scroll_to_bottom(force=True)

    def _extract_user_text(self, content) -> str:
        """Extract text from user message content.

        Handles string, list, and dict content formats.

        Args:
            content: The content to extract text from

        Returns:
            Extracted text string
        """
        if isinstance(content, str):
            return content
        elif isinstance(content, list) and len(content) > 0:
            first_item = content[0]
            if isinstance(first_item, dict):
                return first_item.get("text", "") or first_item.get("data", {}).get("text", "")
        elif isinstance(content, dict):
            return content.get("text", "") or content.get("data", {}).get("text", "")
        return str(content) if content else ""

    # ------------------------------------------------------------------
    # Active state management for incremental loading
    # ------------------------------------------------------------------

    def set_active(self, active: bool):
        """Set the active state of this private chat tab.

        When becoming active, loads any missed messages incrementally.
        """
        if self._is_active == active:
            return

        self._is_active = active
        self.active_changed.emit(active)

        if active:
            # Tab is now active, load any missed messages incrementally
            self._load_incremental_messages()

    def is_active(self) -> bool:
        """Check if this tab is currently active."""
        return self._is_active

    def _sync_last_rendered_offset(self):
        """Set _last_rendered_offset to current storage count (e.g. after initial load or after user stream)."""
        try:
            from agent.crew.crew_member_history_service import crew_member_history_service
            workspace_path = getattr(self.workspace, "workspace_path", None)
            project = self.workspace.get_project() if self.workspace else None
            project_name = project.project_name if project else "default"
            if not workspace_path:
                return
            self._last_rendered_offset = crew_member_history_service.get_latest_line_offset(
                workspace_path, project_name, self.crew_member.crew_title
            )
        except Exception as e:
            logger.debug(f"Could not sync last rendered offset: {e}")

    def _load_incremental_messages(self):
        """Load messages that arrived while the tab was inactive."""
        # Skip if initial history hasn't been loaded yet
        if not self._history_loaded:
            return

        try:
            from agent.crew.crew_member_history_service import crew_member_history_service

            workspace_path = getattr(self.workspace, "workspace_path", None)
            project = self.workspace.get_project() if self.workspace else None
            project_name = project.project_name if project else "default"
            crew_title = self.crew_member.crew_title
            if not workspace_path:
                return

            # Get current total offset
            current_offset = crew_member_history_service.get_latest_line_offset(
                workspace_path, project_name, crew_title
            )

            # Check if there are new messages since last render
            if current_offset <= self._last_rendered_offset:
                return

            # Load messages after the last rendered offset
            new_messages = crew_member_history_service.get_messages_after(
                workspace_path,
                project_name,
                crew_title,
                self._last_rendered_offset,
                count=current_offset - self._last_rendered_offset
            )

            if not new_messages:
                return

            logger.debug(
                f"Loading {len(new_messages)} incremental messages for {crew_title} "
                f"(offset: {self._last_rendered_offset} -> {current_offset})"
            )

            # Render each new message (without update_offset, as offset is set at the end)
            for msg in new_messages:
                self._render_history_message(msg)

            # Update the last rendered offset
            self._last_rendered_offset = current_offset

        except Exception as e:
            logger.error(f"Error loading incremental messages: {e}", exc_info=True)

    # ------------------------------------------------------------------

    def _on_message_submitted(self, message: str):
        if not message or self._is_processing:
            return

        self._add_user_message(message)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._process_message_async(message))
        except RuntimeError:
            QTimer.singleShot(0, lambda: asyncio.ensure_future(self._process_message_async(message)))

    @Slot()
    def _check_prompt_qml_loaded(self):
        if not hasattr(self, "_quick") or self._quick.status() != QQuickWidget.Error:
            return
        errors = [err.toString() for err in self._quick.errors()]
        logger.error("Failed to load private chat QML view: %s", "; ".join(errors))
        self.error_occurred.emit(tr("Failed to load chat input UI."))

    @Slot(int)
    def _on_prompt_qml_status_changed(self, _status):
        self._check_prompt_qml_loaded()

    async def _process_message_async(self, message: str):
        """Send message directly to crew member's chat_stream."""
        self._is_processing = True
        try:
            async for event in self.crew_member.chat_stream(message):
                if self._stream_event_handler:
                    self._stream_event_handler.handle_stream_event(event, None)
        except Exception as e:
            logger.error(f"Error in private chat: {e}", exc_info=True)
            self.error_occurred.emit(f"{tr('Error')}: {str(e)}")
        finally:
            self._is_processing = False
            # Sync offset so switching away and back does not reload and duplicate these messages
            self._sync_last_rendered_offset()

    def _on_error(self, error_message: str):
        if not self._model:
            return
        item = {
            self._model.MESSAGE_ID: str(uuid.uuid4()),
            self._model.SENDER_ID: "system",
            self._model.SENDER_NAME: tr("System"),
            self._model.IS_USER: False,
            self._model.CONTENT: error_message,
            self._model.AGENT_COLOR: "#9a9a9a",
            self._model.AGENT_ICON: "\ue6b3",
            self._model.CREW_METADATA: {},
            self._model.STRUCTURED_CONTENT: [],
            self._model.CONTENT_TYPE: "error",
            self._model.IS_READ: True,
            self._model.CREW_READ_BY: [],
            self._model.TIMESTAMP: None,
            self._model.START_TIME: "",
            self._model.DATE_GROUP: "",
        }
        self._model.add_item(item)

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
        if not self._model:
            return

        updates = {}
        if content is not None:
            item = self._model.get_item(self._model.get_row_by_message_id(message_id) or 0)
            if item:
                current_content = item.get(self._model.CONTENT, "")
                new_content = (current_content + content) if append else content
                updates[self._model.CONTENT] = new_content

        if structured_content is not None:
            item = self._model.get_item(self._model.get_row_by_message_id(message_id) or 0)
            if item:
                current_structured = item.get(self._model.STRUCTURED_CONTENT, [])
                if isinstance(structured_content, list):
                    items = []
                    for sc in structured_content:
                        if hasattr(sc, "to_dict"):
                            items.append(sc.to_dict())
                        elif isinstance(sc, dict):
                            items.append(sc)
                elif hasattr(structured_content, "to_dict"):
                    items = [structured_content.to_dict()]
                elif isinstance(structured_content, dict):
                    items = [structured_content]
                else:
                    items = []

                if is_complete:
                    current_structured = [
                        sc for sc in current_structured
                        if sc.get("content_type") != "typing"
                    ]

                updates[self._model.STRUCTURED_CONTENT] = current_structured + items
                if items:
                    primary_type = items[0].get("content_type", "text")
                    updates[self._model.CONTENT_TYPE] = primary_type

        if error:
            updates[self._model.CONTENT] = f"❌ Error: {error}"
            updates[self._model.CONTENT_TYPE] = "error"

        if updates:
            self._model.update_item(message_id, updates)

        if (is_complete or error) and self._scroll_manager:
            self._scroll_manager.scroll_to_bottom(force=True)

    def get_crew_member(self) -> CrewMember:
        return self.crew_member

    def closeEvent(self, event):
        self._disconnect_history_signal()
        super().closeEvent(event)

    def deleteLater(self):
        self._disconnect_history_signal()
        super().deleteLater()
