"""Stream event handler for chat list.

This module handles stream events from the agent system, routing them
to appropriate handlers based on event type.
"""

import copy
import logging
import uuid
from typing import TYPE_CHECKING, Callable, Optional

from agent.chat.content import (
    ErrorContent,
    TextContent,
    ThinkingContent,
    LlmOutputContent,
    TypingContent,
    TypingState,
    StructureContent,
)
from agent.chat.agent_chat_types import ContentType

if TYPE_CHECKING:
    from app.ui.chat.list.managers.skill_manager import SkillManager
    from app.ui.chat.list.managers.metadata_resolver import MetadataResolver
    from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel

logger = logging.getLogger(__name__)


class StreamEventHandler:
    """Handles stream events from the agent system.

    This class routes stream events to appropriate handlers based on
    event type, managing the interaction between the agent system
    and the chat list UI.

    Event types handled:
    - error: Error messages
    - agent_response: Agent text responses
    - skill_*: Skill lifecycle events (start, progress, end, error)
    - tool_*: Tool execution events (start, progress, end, error)
    - crew_member_typing: Typing indicators
    - content: Generic content events (text, thinking, llm_output)

    Attributes:
        _model: QML model instance
        _skill_manager: Skill manager instance
        _metadata_resolver: Metadata resolver instance
        _update_agent_card_callback: Callback for updating agent cards
        _scroll_to_bottom_callback: Callback for scrolling
    """

    def __init__(
        self,
        model: "QmlAgentChatListModel",
        skill_manager: "SkillManager",
        metadata_resolver: "MetadataResolver",
    ):
        """Initialize the stream event handler.

        Args:
            model: QML model instance
            skill_manager: Skill manager instance
            metadata_resolver: Metadata resolver instance
        """
        self._model = model
        self._skill_manager = skill_manager
        self._metadata_resolver = metadata_resolver

        # Callbacks (to be set by widget)
        self._update_agent_card_callback: Optional[Callable] = None
        self._scroll_to_bottom_callback: Optional[Callable] = None

    def set_callbacks(
        self,
        update_agent_card: Optional[Callable] = None,
        scroll_to_bottom: Optional[Callable] = None,
    ) -> None:
        """Set callbacks for event handling.

        Args:
            update_agent_card: Callback for updating agent cards
            scroll_to_bottom: Callback for scrolling to bottom
        """
        self._update_agent_card_callback = update_agent_card
        self._scroll_to_bottom_callback = scroll_to_bottom

    def handle_stream_event(self, event, session) -> None:
        """Handle stream events.

        Args:
            event: The stream event to handle
            session: The session context
        """
        if event.event_type == "error":
            self._handle_error_event(event)
        elif event.event_type == "agent_response":
            self._handle_agent_response_event(event)
        elif event.event_type in ["skill_start", "skill_progress", "skill_end", "skill_error"]:
            self._skill_manager.handle_skill_event(event)
        elif event.event_type in ["tool_start", "tool_progress", "tool_end", "tool_error"]:
            self._skill_manager.handle_tool_event(event)
        elif event.event_type in ["crew_member_typing", "crew_member_typing_end"]:
            self._handle_typing_event(event)
        elif hasattr(event, "content") and event.content:
            self._handle_content_event(event)

    def _handle_error_event(self, event) -> None:
        """Handle error events.

        Args:
            event: Error event
        """
        run_id = getattr(event, "run_id", "")

        # Prepare error content dict
        if hasattr(event, 'content') and event.content:
            if hasattr(event.content, 'to_dict') and callable(event.content.to_dict):
                error_dict = event.content.to_dict()
            else:
                error_dict = ErrorContent(error_message=str(event.content)).to_dict()
        else:
            error_content = event.data.get("content", event.data.get("error", "Unknown error"))
            error_dict = ErrorContent(error_message=error_content).to_dict()

        # If there's an active skill, add error to its child_contents
        if run_id and self._skill_manager._active_skills.get(run_id):
            skill_info = self._skill_manager._active_skills[run_id]
            message_id = skill_info["message_id"]
            skill_info["child_contents"].append(error_dict)
            self._skill_manager.add_child_to_skill(message_id, error_dict, run_id=run_id)
            return

        # No active skill - handle as standalone error
        message_id = str(uuid.uuid4())
        self._skill_manager.get_or_create_agent_card(message_id, "System", "System")
        if self._update_agent_card_callback:
            self._update_agent_card_callback(
                message_id,
                structured_content=error_dict,
                error=event.data.get("content", event.data.get("error", "Unknown error")),
            )

    def _handle_agent_response_event(self, event) -> None:
        """Handle agent response events.

        Args:
            event: Agent response event
        """
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
        if run_id and self._skill_manager._active_skills.get(run_id):
            skill_info = self._skill_manager._active_skills[run_id]
            message_id = skill_info["message_id"]
            skill_info["child_contents"].append(text_dict)
            self._skill_manager.add_child_to_skill(message_id, text_dict, run_id=run_id)
            return

        # No active skill - handle as standalone content
        message_id = event.data.get("message_id")
        if not message_id:
            message_id = f"response_{session_id}_{uuid.uuid4()}"

        self._skill_manager.get_or_create_agent_card(message_id, sender_name, sender_name)
        if self._update_agent_card_callback:
            self._update_agent_card_callback(message_id, structured_content=text_dict)

    def _handle_typing_event(self, event) -> None:
        """Handle crew_member_typing events to show/hide typing indicator.

        Args:
            event: Typing event
        """
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
            self._skill_manager.get_or_create_agent_card(message_id, sender_name, sender_name)
            # Add TypingContent with START state
            typing_content = TypingContent(state=TypingState.START)
            if self._update_agent_card_callback:
                self._update_agent_card_callback(
                    message_id,
                    structured_content=typing_content,
                    is_complete=False,
                )
            logger.debug(f"Added typing indicator for {sender_name} (message_id: {message_id})")

        elif event.event_type == "crew_member_typing_end":
            # Add TypingContent with END state to mark completion in history
            # Then filter out previous typing indicators to update UI state
            item = self._model.get_item_by_message_id(message_id)
            if item:
                # Remove existing typing START indicators to update UI state
                current_structured = item.get(self._model.STRUCTURED_CONTENT, [])
                filtered_structured = [
                    sc for sc in current_structured
                    if sc.get('content_type') != 'typing'
                ]

                # Add TypingContent with END state to record in history
                typing_end_content = TypingContent(
                    state=TypingState.END,
                    title="Typing",
                    description="Agent processing completed"
                )
                final_structured = filtered_structured + [typing_end_content.to_dict()]

                self._model.update_item(message_id, {
                    self._model.STRUCTURED_CONTENT: final_structured,
                })
                # Force immediate UI update to ensure typing state changes
                self._model.flush_updates()
                logger.debug(f"Added typing_end indicator for {sender_name} (message_id: {message_id})")
            else:
                logger.warning(f"[typing_end] Item not found for message_id: {message_id}")

    def _handle_content_event(self, event) -> None:
        """Handle events with content.

        Args:
            event: Content event
        """
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
        if run_id and self._skill_manager._active_skills.get(run_id):
            skill_info = self._skill_manager._active_skills[run_id]
            message_id = skill_info["message_id"]
            skill_info["child_contents"].append(content_dict)
            self._skill_manager.add_child_to_skill(message_id, content_dict, run_id=run_id)
            return

        # No active skill - handle as standalone content
        item = self._model.get_item_by_message_id(event.message_id)
        if not item:
            agent_name = getattr(event, "agent_name", "Unknown")
            self._skill_manager.get_or_create_agent_card(
                event.message_id,
                agent_name,
                getattr(event, "title", None),
            )

        if self._update_agent_card_callback:
            self._update_agent_card_callback(event.message_id, structured_content=content_dict)
