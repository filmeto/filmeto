"""Private chat widget for 1-on-1 conversations with a crew member.

This widget provides a dedicated chat interface for direct messaging
with an individual crew member, using their chat_stream interface.
Messages are stored in the crew member's own history and do NOT
leak into the group chat.
"""

import asyncio
import logging
import uuid

from PySide6.QtWidgets import QVBoxLayout, QSplitter
from PySide6.QtCore import Qt, Signal, QTimer

from agent.crew import CrewMember
from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from app.ui.chat.list import QmlAgentChatListWidget
from app.ui.prompt.agent_prompt_widget import AgentPromptWidget
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)


class PrivateChatWidget(BaseWidget):
    """Chat widget for private 1-on-1 conversation with a crew member."""

    error_occurred = Signal(str)

    def __init__(self, workspace: Workspace, crew_member: CrewMember, parent=None):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        self.crew_member = crew_member
        self._is_processing = False

        self.error_occurred.connect(self._on_error)
        self._setup_ui()

        QTimer.singleShot(200, self._load_history)

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
                return

            messages.reverse()

            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                sender_name = msg.get("sender_name", "")
                message_id = msg.get("message_id", str(uuid.uuid4()))
                is_event = msg.get("is_event", False)
                timestamp = msg.get("timestamp", None)

                if not content:
                    continue

                if role == "user":
                    self.chat_list_widget.add_user_message(content, timestamp=timestamp)
                elif role == "event":
                    # Handle event messages with structured content
                    self._load_event_message(msg)
                else:
                    self.chat_list_widget.append_message(
                        sender_name or self.crew_member.config.name,
                        content,
                        message_id=message_id,
                        timestamp=timestamp
                    )

        except Exception as e:
            logger.error(f"Error loading private chat history: {e}", exc_info=True)

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
            run_id = msg.get("run_id", "")
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
                def __init__(self, event_type, sender_id, sender_name, run_id, content):
                    self.event_type = event_type
                    self.sender_id = sender_id
                    self.sender_name = sender_name
                    self.run_id = run_id
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
                run_id=run_id,
                content=content
            )

            # Use the chat list widget's handle_stream_event to render the event
            self.chat_list_widget.handle_stream_event(mock_event, None)

            # Update the message timestamp if available
            # Use run_id as the message_id since that's what handle_stream_event uses
            if timestamp and run_id:
                model = self.chat_list_widget._model
                model.update_item(run_id, {
                    model.TIMESTAMP: timestamp,
                })

        except Exception as e:
            logger.error(f"Error loading event message: {e}", exc_info=True)

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

    def _on_error(self, error_message: str):
        if self.chat_list_widget:
            self.chat_list_widget.append_message(tr("System"), error_message)

    def get_crew_member(self) -> CrewMember:
        return self.crew_member
