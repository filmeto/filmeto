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
from typing import Dict, Any

from PySide6.QtWidgets import QVBoxLayout, QSplitter
from PySide6.QtCore import Qt, Signal, QTimer

from agent.crew import CrewMember
from agent.crew.crew_member_history_service import crew_member_message_saved
from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from app.ui.chat.list import QmlAgentChatListWidget
from app.ui.prompt.agent_prompt_widget import AgentPromptWidget
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)


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

        self.error_occurred.connect(self._on_error)
        self._new_history_message.connect(self._render_history_message)
        self._setup_ui()
        self._connect_history_signal()

        QTimer.singleShot(200, self._load_history)

    @staticmethod
    def _is_structured_content(content) -> bool:
        """Check if content is structured (has content_type).

        Structured content should be rendered via handle_stream_event,
        while plain text content can be rendered directly.

        Args:
            content: The content to check (can be any type)

        Returns:
            True if content is a dict with content_type, False otherwise
        """
        return isinstance(content, dict) and "content_type" in content

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setObjectName("private_chat_splitter")
        self.splitter.setHandleWidth(0)

        self.chat_list_widget = QmlAgentChatListWidget(self.workspace, self)
        self.chat_list_widget.setObjectName("private_chat_list_widget")
        self.splitter.addWidget(self.chat_list_widget)

        self.prompt_widget = AgentPromptWidget(self.workspace, self)
        self.prompt_widget.setObjectName("private_chat_prompt_widget")
        self.splitter.addWidget(self.prompt_widget)

        QTimer.singleShot(0, lambda: self.splitter.setSizes([600, 200]))
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)

        layout.addWidget(self.splitter)

        self.prompt_widget.message_submitted.connect(self._on_message_submitted)

    def _load_history(self):
        """Load the crew member's chat history into the display."""
        try:
            self.chat_list_widget.clear()

            messages = self.crew_member.get_history_latest(100)
            if not messages:
                self._sync_last_rendered_offset()
                self._history_loaded = True
                return

            messages.reverse()

            for msg in messages:
                self._render_message(msg)

            self._sync_last_rendered_offset()
            self._history_loaded = True

        except Exception as e:
            logger.error(f"Error loading private chat history: {e}", exc_info=True)
            self._history_loaded = True

    def _load_event_message(self, msg: dict):
        """Load an event message from history.

        Args:
            msg: The event message dictionary containing event details
        """
        try:
            from agent.chat.content import StructureContent
            from agent.chat.agent_chat_types import ContentType

            event_type = msg.get("event_type", "")
            sender_name = msg.get("sender_name", self.crew_member.config.name)
            sender_id = msg.get("sender_id", self.crew_member.config.name)
            message_id = msg.get("message_id", str(uuid.uuid4()))
            content_dict = msg.get("content", {})
            timestamp = msg.get("timestamp", None)

            if not content_dict:
                return

            # Convert content dict to StructureContent
            content_type_str = content_dict.get("content_type", "text")
            try:
                content_type = ContentType(content_type_str)
            except ValueError:
                content_type = ContentType.TEXT

            # Create a mock event object for handle_stream_event
            class MockEvent:
                def __init__(self, event_type, sender_id, sender_name, content, message_id):
                    self.event_type = event_type
                    self.sender_id = sender_id
                    self.sender_name = sender_name
                    self.content = content
                    self.message_id = message_id

            # Create StructureContent from dict
            if isinstance(content_dict, dict):
                content = StructureContent.from_dict(content_dict)
            else:
                from agent.chat.content import TextContent
                content = TextContent(text=str(content_dict))

            mock_event = MockEvent(
                event_type=event_type,
                sender_id=sender_id,
                sender_name=sender_name,
                content=content,
                message_id=message_id
            )

            # Use the chat list widget's handle_stream_event to render the event
            self.chat_list_widget.handle_stream_event(mock_event, None)

            # Update the message timestamp and formatted startTime if available
            if timestamp and message_id:
                from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
                model = self.chat_list_widget._model
                model.update_item(message_id, {
                    model.TIMESTAMP: timestamp,
                    model.START_TIME: QmlAgentChatListModel._format_start_time(timestamp),
                })

        except Exception as e:
            logger.error(f"Error loading event message: {e}", exc_info=True)

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

        Uses content structure (content_type) to determine rendering method:
        - User messages: add_user_message()
        - Structured content (has content_type): handle_stream_event()
        - Plain text: append_message()

        Args:
            msg: The message dictionary to render
        """
        sender_id = msg.get("sender_id", "")
        content = msg.get("content", "")
        sender_name = msg.get("sender_name", "")
        message_id = msg.get("message_id", str(uuid.uuid4()))
        timestamp = msg.get("timestamp", None)

        if not content:
            return

        # User messages are handled separately
        if sender_id and sender_id.lower() == "user":
            self.chat_list_widget.add_user_message(content, timestamp=timestamp)
            return

        # Check if content is structured (has content_type)
        if self._is_structured_content(content):
            # Structured content: use handle_stream_event for proper rendering
            self._load_event_message(msg)
        else:
            # Plain text content: render directly
            self.chat_list_widget.append_message(
                sender_name or self.crew_member.config.name,
                content,
                message_id=message_id,
                timestamp=timestamp,
            )

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

        self.chat_list_widget.add_user_message(message)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._process_message_async(message))
        except RuntimeError:
            QTimer.singleShot(0, lambda: asyncio.ensure_future(self._process_message_async(message)))

    async def _process_message_async(self, message: str):
        """Send message directly to crew member's chat_stream."""
        self._is_processing = True
        try:
            async for event in self.crew_member.chat_stream(message):
                self.chat_list_widget.handle_stream_event(event, None)
        except Exception as e:
            logger.error(f"Error in private chat: {e}", exc_info=True)
            self.error_occurred.emit(f"{tr('Error')}: {str(e)}")
        finally:
            self._is_processing = False
            # Sync offset so switching away and back does not reload and duplicate these messages
            self._sync_last_rendered_offset()

    def _on_error(self, error_message: str):
        if self.chat_list_widget:
            self.chat_list_widget.append_message(tr("System"), error_message)

    def get_crew_member(self) -> CrewMember:
        return self.crew_member

    def closeEvent(self, event):
        self._disconnect_history_signal()
        super().closeEvent(event)

    def deleteLater(self):
        self._disconnect_history_signal()
        super().deleteLater()
