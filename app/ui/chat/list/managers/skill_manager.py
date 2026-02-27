"""Skill lifecycle manager for chat list.

This module handles skill event processing, including skill lifecycle
tracking, content merging, and child content management.
"""

import copy
import logging
import uuid
from typing import Dict, List, Any, Optional, TYPE_CHECKING, Callable

from agent.chat.content import (
    SkillContent,
    SkillExecutionState,
    ContentStatus,
    ToolCallContent,
    TextContent,
)

if TYPE_CHECKING:
    from app.ui.chat.list.managers.metadata_resolver import MetadataResolver
    from app.ui.chat.list.managers.scroll_manager import ScrollManager
    from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel

logger = logging.getLogger(__name__)


class SkillManager:
    """Manages skill lifecycle and content merging for the chat list.

    This class handles:
    - Active skill tracking by run_id
    - Skill name to message_id mapping
    - Skill event handling (start/progress/end/error)
    - Tool event handling as children of skills
    - Skill content merging with state priority
    - Agent card creation and finalization

    Attributes:
        _model: QML model instance
        _metadata_resolver: Resolver for crew member metadata
        _scroll_manager: Scroll manager for auto-scrolling
        _active_skills: Active skills by run_id
        _skill_name_to_message_id: Mapping of skill name to message_id
        _agent_current_cards: Current agent card by agent name
        _active_tools: Active tools by tool_call_id for merging events
    """

    def __init__(
        self,
        model: "QmlAgentChatListModel",
        metadata_resolver: "MetadataResolver",
        scroll_manager: "ScrollManager",
    ):
        """Initialize the skill manager.

        Args:
            model: QML model instance
            metadata_resolver: Resolver for crew member metadata
            scroll_manager: Scroll manager for auto-scrolling
        """
        self._model = model
        self._metadata_resolver = metadata_resolver
        self._scroll_manager = scroll_manager

        # Active skills tracking: {run_id: {message_id, skill_name, sender_name, state, child_contents}}
        self._active_skills: Dict[str, Dict[str, Any]] = {}
        # Skill name to message_id mapping for combining skills: {skill_name: message_id}
        self._skill_name_to_message_id: Dict[str, str] = {}
        # Current agent cards: {agent_name: message_id}
        self._agent_current_cards: Dict[str, str] = {}
        # Active tools tracking for merging: {tool_call_id: {run_id, message_id, tool_name, status}}
        self._active_tools: Dict[str, Dict[str, Any]] = {}

    def handle_skill_event(self, event) -> None:
        """Handle skill events - tracks skill lifecycle with start/progress/end/error.

        Each skill execution is represented by a single SkillContent that:
        - Gets created on skill_start
        - Gets updated on skill_progress
        - Gets finalized on skill_end or skill_error
        - Collects child contents (tool calls, etc.) during execution

        Args:
            event: Skill event from the stream
        """
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
            skill_name = skill_content.skill_name
            sender_name = getattr(event, 'sender_name', 'Unknown')
            sender_id = getattr(event, 'sender_id', sender_name.lower())
            message_id = f"skill_{run_id}_{skill_name}"

            if sender_id == "user":
                return

        # Handle different event types
        if event.event_type == "skill_start":
            # Check if there's already a message for this skill name
            if skill_name in self._skill_name_to_message_id:
                message_id = self._skill_name_to_message_id[skill_name]
            else:
                self._skill_name_to_message_id[skill_name] = message_id

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
                if skill_name in self._skill_name_to_message_id:
                    message_id = self._skill_name_to_message_id[skill_name]
                else:
                    self._skill_name_to_message_id[skill_name] = message_id

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
            self._finalize_skill(run_id, skill_name, message_id, sender_name, skill_content)

        elif event.event_type == "skill_error":
            # Finalize the skill with error
            if run_id in self._active_skills:
                self._active_skills[run_id]["state"] = SkillExecutionState.ERROR
                skill_content.child_contents = self._active_skills[run_id]["child_contents"]
                self._update_skill_content(message_id, skill_content)
                del self._active_skills[run_id]
                self._cleanup_skill_name_mapping(skill_name)
            else:
                # Skill error without start - create new
                if skill_name in self._skill_name_to_message_id:
                    message_id = self._skill_name_to_message_id[skill_name]
                else:
                    self._skill_name_to_message_id[skill_name] = message_id

                self.get_or_create_agent_card(message_id, sender_name, sender_name)
                self._update_skill_content(message_id, skill_content, create_new=True)
                self._cleanup_skill_name_mapping(skill_name)

    def handle_tool_event(self, event) -> None:
        """Handle tool events - merges tool lifecycle events by tool_call_id.

        Tool events (tool_start, tool_progress, tool_end, tool_error) are
        associated with the active skill via run_id and stored as child contents.
        Events with the same tool_call_id are merged using state priority:
        failed > completed > started

        Args:
            event: Tool event from the stream
        """
        run_id = getattr(event, "run_id", "")
        step_id = getattr(event, "step_id", 0)

        # Check if this tool belongs to an active skill
        if run_id not in self._active_skills:
            logger.debug(f"Tool event without active skill: run_id={run_id}")
            return

        skill_info = self._active_skills[run_id]
        message_id = skill_info["message_id"]

        # Get tool_name from event.content if available, fallback to event attribute or event.data
        tool_name = "unknown"
        if hasattr(event, 'content') and event.content and hasattr(event.content, 'tool_name'):
            tool_name = event.content.tool_name or "unknown"
        elif hasattr(event, 'tool_name'):
            tool_name = event.tool_name
        elif hasattr(event, 'data'):
            tool_name = event.data.get("tool_name", "unknown")

        # Get or generate tool_call_id for tracking
        # Use event.content.tool_call_id if available, otherwise generate from run_id + step_id + tool_name

        if hasattr(event, 'content') and event.content and hasattr(event.content, 'tool_call_id') and event.content.tool_call_id:
            tool_call_id = event.content.tool_call_id
        else:
            # Generate tool_call_id from run_id + step_id + tool_name for legacy events
            tool_call_id = f"{run_id}_{step_id}_{tool_name}"

        # Create tool content from event
        tool_content = None
        if event.event_type == "tool_start":
            # Get tool_input from event.content if available, fallback to event.data
            tool_input = {}
            if hasattr(event, 'content') and event.content and hasattr(event.content, 'tool_input'):
                tool_input = event.content.tool_input or {}
            elif hasattr(event, 'data'):
                tool_input = event.data.get("tool_input", {})

            tool_content = ToolCallContent(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_status="started",
                tool_call_id=tool_call_id,
            )
            # Track the active tool
            self._active_tools[tool_call_id] = {
                "run_id": run_id,
                "message_id": message_id,
                "tool_name": tool_name,
                "status": "started",
            }

        elif event.event_type == "tool_progress":
            # Progress events update existing tool content
            if tool_call_id in self._active_tools:
                # Update progress without creating new entry
                progress_msg = ""
                if hasattr(event, 'content') and event.content and hasattr(event.content, 'progress'):
                    progress_msg = event.content.progress or ""
                elif hasattr(event, 'data'):
                    progress_msg = event.data.get('progress', '')
                logger.debug(f"Tool progress for {tool_name}: {progress_msg}")
            return  # Don't add progress as separate child content

        elif event.event_type == "tool_end":
            # Get tool_input from event.content if available, fallback to event.data
            tool_input = {}
            result = None
            if hasattr(event, 'content') and event.content:
                if hasattr(event.content, 'tool_input'):
                    tool_input = event.content.tool_input or {}
                if hasattr(event.content, 'result'):
                    result = event.content.result
            elif hasattr(event, 'data'):
                tool_input = event.data.get("tool_input", {})
                result = event.data.get("result")

            tool_content = ToolCallContent(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_status="completed",
                result=result,
                tool_call_id=tool_call_id,
            )
            # Update tracking and cleanup
            if tool_call_id in self._active_tools:
                self._active_tools[tool_call_id]["status"] = "completed"

        elif event.event_type == "tool_error":
            # Get tool_input and error from event.content if available, fallback to event.data
            tool_input = {}
            error_msg = "Tool execution failed"
            if hasattr(event, 'content') and event.content:
                if hasattr(event.content, 'tool_input'):
                    tool_input = event.content.tool_input or {}
                if hasattr(event.content, 'error'):
                    error_msg = event.content.error or error_msg
            elif hasattr(event, 'data'):
                tool_input = event.data.get("tool_input", {})
                error_msg = event.data.get("error", error_msg)

            tool_content = ToolCallContent(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_status="failed",
                error=error_msg,
                tool_call_id=tool_call_id,
            )
            # Update tracking and cleanup
            if tool_call_id in self._active_tools:
                self._active_tools[tool_call_id]["status"] = "failed"

        if tool_content:
            tool_dict = tool_content.to_dict()
            # Use merge logic instead of simple append
            self._add_or_merge_tool_child(message_id, tool_dict, run_id, tool_call_id)

    def _add_or_merge_tool_child(
        self,
        message_id: str,
        tool_content: Dict[str, Any],
        run_id: str,
        tool_call_id: str
    ) -> None:
        """Add or merge tool content in skill's child_contents.

        If a tool with the same tool_call_id already exists, merge using
        state priority. Otherwise, add as new child.

        Args:
            message_id: The message ID containing the skill
            tool_content: The tool content dictionary
            run_id: The run_id to identify which skill to update
            tool_call_id: Unique identifier for the tool call
        """
        item = self._model.get_item(self._model.get_row_by_message_id(message_id) or 0)
        if not item:
            return

        current_structured = item.get(self._model.STRUCTURED_CONTENT, [])
        new_structured = []

        for sc in current_structured:
            if sc.get("content_type") == "skill":
                sc_data = sc.get("data", {})
                # If run_id is provided, only update matching skills
                if run_id is not None:
                    if sc_data.get("run_id") != run_id:
                        new_structured.append(copy.deepcopy(sc))
                        continue

                # Check for existing tool with same tool_call_id
                child_contents = list(sc_data.get("child_contents", []))
                existing_tool_index = -1

                for i, child in enumerate(child_contents):
                    if child.get("content_type") == "tool_call":
                        child_data = child.get("data", {})
                        if child_data.get("tool_call_id") == tool_call_id:
                            existing_tool_index = i
                            break

                if existing_tool_index >= 0:
                    # Merge with existing tool content
                    merged_tool = self._merge_tool_content_with_existing(
                        child_contents[existing_tool_index],
                        tool_content
                    )
                    child_contents[existing_tool_index] = merged_tool
                else:
                    # Add new tool content
                    child_contents.append(copy.deepcopy(tool_content))

                # Update skill with merged child contents
                new_sc = copy.deepcopy(sc)
                new_sc["data"]["child_contents"] = child_contents
                new_structured.append(new_sc)
            else:
                new_structured.append(copy.deepcopy(sc))

        self._model.update_item(message_id, {
            self._model.STRUCTURED_CONTENT: new_structured,
        })

    def _merge_tool_content_with_existing(
        self,
        existing_entry: Dict[str, Any],
        new_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge existing tool entry with new tool content using state priority.

        State priority: failed > completed > started

        Args:
            existing_entry: Existing tool entry (dict format)
            new_content: New tool content dictionary

        Returns:
            Merged tool entry in dict format (deep copied)
        """
        existing_data = existing_entry.get("data", {})
        new_data = new_content.get("data", {})

        existing_status = existing_data.get("status", "started")
        new_status = new_data.get("status", "started")

        # Get state priority
        state_priority = self._get_tool_state_priority()
        existing_priority = state_priority.get(existing_status, 0)
        new_priority = state_priority.get(new_status, 0)

        # Determine which entry to use as base based on state priority
        if new_priority >= existing_priority:
            # New state has higher or equal priority, use new content as base
            # but preserve tool_input from existing if new doesn't have it
            merged_dict = copy.deepcopy(new_content)
            merged_data = merged_dict.get("data", {})

            # Preserve tool_input from existing if new doesn't have it
            if not merged_data.get("tool_input") and existing_data.get("tool_input"):
                merged_data["tool_input"] = copy.deepcopy(existing_data.get("tool_input", {}))

            merged_dict["data"] = merged_data
        else:
            # Existing state has higher priority, keep existing
            merged_dict = copy.deepcopy(existing_entry)

        return merged_dict

    def _get_tool_state_priority(self) -> Dict[str, int]:
        """Get the priority mapping for tool execution states.

        Returns:
            Dictionary mapping state values to priority levels (higher = more important)
        """
        return {
            "failed": 3,
            "completed": 2,
            "started": 1,
        }

    def get_or_create_agent_card(
        self,
        message_id: str,
        agent_name: str,
        title: Optional[str] = None
    ) -> str:
        """Get or create an agent message card.

        Args:
            message_id: The message ID for the card
            agent_name: The name of the agent
            title: Optional title for the card

        Returns:
            The message_id of the card
        """
        existing_row = self._model.get_row_by_message_id(message_id)
        if existing_row is not None:
            return message_id

        # Finalize the previous card so its typing indicator reaches terminal state
        self._finalize_previous_agent_card(agent_name)

        agent_color, agent_icon, crew_member_data = self._metadata_resolver.resolve_agent_metadata(agent_name)

        item = {
            self._model.MESSAGE_ID: message_id,
            self._model.SENDER_ID: agent_name,
            self._model.SENDER_NAME: agent_name,
            self._model.IS_USER: False,
            self._model.CONTENT: "",
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
        self._agent_current_cards[agent_name] = message_id
        self._scroll_manager.scroll_to_bottom(force=True)
        return message_id

    def _finalize_previous_agent_card(self, agent_name: str) -> None:
        """Remove typing indicators from the previous card of an agent.

        When a new message starts, the previous message should reach its
        terminal state (no more bouncing dots).

        Args:
            agent_name: The name of the agent
        """
        prev_message_id = self._agent_current_cards.get(agent_name)
        if not prev_message_id:
            return
        prev_item = self._model.get_item_by_message_id(prev_message_id)
        if not prev_item:
            return
        current_structured = prev_item.get(self._model.STRUCTURED_CONTENT, [])
        has_typing = any(
            sc.get('content_type') == 'typing' for sc in current_structured
        )
        if has_typing:
            filtered = [
                sc for sc in current_structured
                if sc.get('content_type') != 'typing'
            ]
            self._model.update_item(prev_message_id, {
                self._model.STRUCTURED_CONTENT: filtered,
            })

    def _update_skill_content(
        self,
        message_id: str,
        skill_content: SkillContent,
        create_new: bool = False
    ) -> None:
        """Update existing skill content with new state.

        Uses the same merging strategy as historical loading to ensure
        consistency between historical loading and real-time updates.

        Args:
            message_id: The message ID containing the skill
            skill_content: New SkillContent with updated state
            create_new: If True, always create new content instead of replacing
        """
        item = self._model.get_item(self._model.get_row_by_message_id(message_id) or 0)
        if not item:
            return

        current_structured = item.get(self._model.STRUCTURED_CONTENT, [])

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
            # Found existing skill - merge using the same logic as historical loading
            merged_entry = self._merge_skill_content_with_existing(
                existing_skill_entry,
                skill_content
            )
            # Deep copy all elements to ensure QML detects the change
            new_structured = [copy.deepcopy(sc) for sc in current_structured]
            new_structured[existing_skill_index] = merged_entry
        elif create_new:
            # No existing skill and create_new is True - append new
            new_structured = [copy.deepcopy(sc) for sc in current_structured]
            new_structured.append(skill_content.to_dict())
        else:
            # No existing skill and create_new is False - append anyway
            new_structured = [copy.deepcopy(sc) for sc in current_structured]
            new_structured.append(skill_content.to_dict())

        self._model.update_item(message_id, {
            self._model.STRUCTURED_CONTENT: new_structured,
        })

    def _merge_skill_content_with_existing(
        self,
        existing_entry: Dict[str, Any],
        new_content: SkillContent
    ) -> Dict[str, Any]:
        """Merge existing skill entry with new skill content.

        Uses the same merging strategy as historical loading to ensure
        consistency between historical loading and real-time updates.

        Args:
            existing_entry: Existing skill entry (dict format from storage)
            new_content: New SkillContent object

        Returns:
            Merged skill entry in dict format (deep copied to ensure QML detects changes)
        """
        existing_data = existing_entry.get("data", {})
        existing_state = existing_data.get("state", SkillExecutionState.PENDING.value)
        new_state = new_content.state.value if isinstance(new_content.state, SkillExecutionState) else new_content.state

        # Get state priority using common utility
        state_priority = self._get_skill_state_priority()
        existing_priority = state_priority.get(existing_state, 0)
        new_priority = state_priority.get(new_state, 0)

        # Get child_contents from both sources (deep copy to avoid reference sharing)
        existing_children = copy.deepcopy(existing_data.get("child_contents", []))
        new_children = copy.deepcopy(new_content.child_contents or [])

        # Determine which entry to use as base based on state priority
        if new_priority > existing_priority:
            # New state has higher priority, use new content as base
            merged_dict = new_content.to_dict()
            merged_data = merged_dict.get("data", {})
            if not merged_data.get("child_contents"):
                merged_data["child_contents"] = existing_children
            else:
                # Merge child contents: new children take precedence, add unique existing ones
                merged_children = self._merge_child_contents_by_id(
                    merged_data.get("child_contents", []),
                    existing_children
                )
                merged_data["child_contents"] = merged_children
            merged_dict["data"] = merged_data

        elif new_priority < existing_priority:
            # Existing state has higher priority, keep existing but update certain fields
            if (new_state == SkillExecutionState.IN_PROGRESS.value and
                existing_state == SkillExecutionState.IN_PROGRESS.value):
                # Both are in_progress, update with latest progress info
                merged_dict = copy.deepcopy(existing_entry)
                merged_data = merged_dict.get("data", {})
                merged_data.update({
                    "progress_text": new_content.progress_text,
                    "progress_percentage": new_content.progress_percentage,
                })
                if new_children:
                    merged_children = self._merge_child_contents_by_id(
                        existing_children,
                        new_children
                    )
                    merged_data["child_contents"] = merged_children
                else:
                    merged_data["child_contents"] = existing_children
                merged_dict["data"] = merged_data
            else:
                merged_dict = copy.deepcopy(existing_entry)

        else:
            # Same priority - use the new content as it's more recent
            merged_dict = new_content.to_dict()
            merged_data = merged_dict.get("data", {})
            if not merged_data.get("child_contents"):
                merged_data["child_contents"] = existing_children
            else:
                merged_children = self._merge_child_contents_by_id(
                    merged_data.get("child_contents", []),
                    existing_children
                )
                merged_data["child_contents"] = merged_children
            merged_dict["data"] = merged_data

        # Deep copy final result to ensure QML detects the change
        return copy.deepcopy(merged_dict)

    def add_child_to_skill(
        self,
        message_id: str,
        child_content: Dict[str, Any],
        run_id: Optional[str] = None
    ) -> None:
        """Add a child content to the skill's child_contents list.

        Args:
            message_id: The message ID containing the skill
            child_content: The child content dictionary to add
            run_id: Optional run_id to identify which skill to update.
                    If not provided, adds to all skills (legacy behavior).
        """
        item = self._model.get_item(self._model.get_row_by_message_id(message_id) or 0)
        if not item:
            return

        current_structured = item.get(self._model.STRUCTURED_CONTENT, [])
        new_structured = []

        for sc in current_structured:
            if sc.get("content_type") == "skill":
                sc_data = sc.get("data", {})
                # If run_id is provided, only update matching skills
                if run_id is not None:
                    if sc_data.get("run_id") != run_id:
                        new_structured.append(copy.deepcopy(sc))
                        continue

                # Add child content to the skill
                new_sc = copy.deepcopy(sc)
                sc_data = new_sc.get("data", {})
                child_contents = list(sc_data.get("child_contents", []))

                # Avoid duplicates by content_id
                child_id = child_content.get("content_id")
                if child_id:
                    existing_ids = {c.get("content_id") for c in child_contents if c.get("content_id")}
                    if child_id not in existing_ids:
                        child_contents.append(copy.deepcopy(child_content))
                else:
                    child_contents.append(copy.deepcopy(child_content))

                sc_data["child_contents"] = child_contents
                new_sc["data"] = sc_data
                new_structured.append(new_sc)
            else:
                new_structured.append(copy.deepcopy(sc))

        self._model.update_item(message_id, {
            self._model.STRUCTURED_CONTENT: new_structured,
        })

    def _get_skill_state_priority(self) -> Dict[str, int]:
        """Get the priority mapping for skill execution states.

        Returns:
            Dictionary mapping state values to priority levels (higher = more important)
        """
        return {
            SkillExecutionState.ERROR.value: 4,
            SkillExecutionState.COMPLETED.value: 3,
            SkillExecutionState.IN_PROGRESS.value: 2,
            SkillExecutionState.PENDING.value: 1,
        }

    def _merge_child_contents_by_id(
        self,
        base_children: List[Dict[str, Any]],
        new_children: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge child contents, deduplicating by content_id.

        Args:
            base_children: Base list of children (typically existing/new content)
            new_children: New children to merge in

        Returns:
            Merged list with unique children (deep copied)
        """
        all_children = []
        seen_ids = set()

        # Add base children first
        for child in base_children:
            child_id = child.get("content_id") if isinstance(child, dict) else None
            all_children.append(copy.deepcopy(child))
            if child_id:
                seen_ids.add(child_id)

        # Add new children not already present
        for child in new_children:
            child_id = child.get("content_id") if isinstance(child, dict) else None
            if child_id and child_id in seen_ids:
                continue
            all_children.append(copy.deepcopy(child))
            if child_id:
                seen_ids.add(child_id)

        return all_children

    def _finalize_skill(
        self,
        run_id: str,
        skill_name: str,
        message_id: str,
        sender_name: str,
        skill_content: SkillContent
    ) -> None:
        """Finalize a skill (on skill_end event).

        Args:
            run_id: The run_id of the skill
            skill_name: The name of the skill
            message_id: The message ID for the skill
            sender_name: The sender name
            skill_content: The skill content to finalize
        """
        if run_id in self._active_skills:
            self._active_skills[run_id]["state"] = SkillExecutionState.COMPLETED
            skill_content.child_contents = self._active_skills[run_id]["child_contents"]
            self._update_skill_content(message_id, skill_content)
            del self._active_skills[run_id]
            self._cleanup_skill_name_mapping(skill_name)
        else:
            # Skill end without start - create new
            if skill_name in self._skill_name_to_message_id:
                message_id = self._skill_name_to_message_id[skill_name]
            else:
                self._skill_name_to_message_id[skill_name] = message_id

            self.get_or_create_agent_card(message_id, sender_name, sender_name)
            self._update_skill_content(message_id, skill_content, create_new=True)
            self._cleanup_skill_name_mapping(skill_name)

    def _cleanup_skill_name_mapping(self, skill_name: str) -> None:
        """Clean up skill name mapping if this was the last skill with this name.

        Args:
            skill_name: The name of the skill to check
        """
        for r_id, skill_info in self._active_skills.items():
            if skill_info["skill_name"] == skill_name:
                break
        else:
            # No other active skills with this name exist, remove from mapping
            if skill_name in self._skill_name_to_message_id:
                del self._skill_name_to_message_id[skill_name]

    def clear(self) -> None:
        """Clear all skill tracking state."""
        self._active_skills.clear()
        self._skill_name_to_message_id.clear()
        self._agent_current_cards.clear()
        self._active_tools.clear()
