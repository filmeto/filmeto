"""
Filmeto Agent Routing Module

Handles message routing, crew member streaming, and LLM-based routing decisions.
"""
import asyncio
import logging
import uuid
from typing import AsyncGenerator, Dict, List, Optional, Any, TYPE_CHECKING

from agent.chat.agent_chat_message import AgentMessage
from agent.chat.content import (
    StructureContent, TextContent, ThinkingContent, ToolCallContent,
    ToolResponseContent, ProgressContent, MetadataContent, ErrorContent,
    LlmOutputContent, TodoWriteContent, CrewMemberReadContent
)
from agent.chat.agent_chat_types import ContentType
from agent.core.filmeto_constants import PRODUCER_NAME
from agent.core.filmeto_utils import extract_text_content
from agent.router.message_target import MessageTarget, TargetType
from agent.router.message_router_service import RoutingDecision

if TYPE_CHECKING:
    from agent.crew.crew_member import CrewMember
    from agent.event.agent_event import AgentEvent
    from agent.react.types import AgentEventType
    from agent.router.message_router_service import MessageRouterService
    from agent.core.filmeto_crew import FilmetoCrewManager
    from agent.chat.agent_chat_signals import AgentChatSignals

logger = logging.getLogger(__name__)


MAX_ROUTING_DEPTH = 5  # Maximum hops before the routing chain is forcibly terminated


class FilmetoRoutingManager:
    """
    Manages message routing and crew member streaming for FilmetoAgent.
    """

    def __init__(
        self,
        crew_manager: "FilmetoCrewManager",
        message_router: "MessageRouterService",
        signals: "AgentChatSignals",
        conversation_history: List[AgentMessage],
    ):
        """Initialize the routing manager."""
        self._crew_manager = crew_manager
        self._message_router = message_router
        self._signals = signals
        self._conversation_history = conversation_history
        # Per-session routing state: session_id -> (depth, visited_senders frozenset)
        self._routing_state: Dict[str, Any] = {}

    async def stream_crew_member(
        self,
        crew_member: "CrewMember",
        message: str,
        plan_id: Optional[str],
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        message_id: Optional[str] = None,
        record_to_agent_history: bool = True,
        send_main_content_to_agent: bool = False,
        routing_depth: int = 0,
        visited_senders: Optional[frozenset] = None,
    ) -> AsyncGenerator["AgentEvent", None]:
        """
        Stream responses from a crew member.

        Args:
            crew_member: The crew member to stream from
            message: The message to send
            plan_id: Optional plan ID for context
            session_id: Session ID for this conversation
            metadata: Optional metadata to attach to events
            message_id: Optional message ID (generated if not provided)
            record_to_agent_history: Whether to record to agent history
            send_main_content_to_agent: Whether to send collected main content to agent
            routing_depth: Current hop depth in the routing chain (loop protection)
            visited_senders: Set of sender IDs already seen in this chain (cycle detection)

        Yields:
            AgentEvent objects
        """
        from agent.react import AgentEvent, AgentEventType

        # Set the current message ID on the crew member for content tracking
        if message_id is None:
            message_id = str(uuid.uuid4())
        crew_member._current_message_id = message_id

        # Track content IDs for hierarchical relationships
        content_tracking: Dict[str, str] = {}

        # Track active skill execution
        _active_skill_name: Optional[str] = None

        # Track main content for sending to agent
        _collected_main_content: List[StructureContent] = []

        # Group chat routing: use sender_id="system" to indicate routed message
        # Always record to crew member's private history for full traceability
        async for event in crew_member.chat_stream(
            message,
            plan_id=plan_id,
            sender_id="system",
            sender_name="System",
            message_id=message_id,
            record_to_private_history=True,
        ):
            # Add metadata to the event payload
            event_payload = dict(event.payload)
            if metadata:
                event_payload.update(metadata)
            if plan_id:
                event_payload["plan_id"] = plan_id

            # Track skill execution boundaries
            if event.event_type in (AgentEventType.SKILL_START.value, AgentEventType.SKILL_START):
                if event.content and hasattr(event.content, "skill_name"):
                    _active_skill_name = event.content.skill_name
            elif event.event_type in (
                AgentEventType.SKILL_END.value, AgentEventType.SKILL_END,
                AgentEventType.SKILL_ERROR.value, AgentEventType.SKILL_ERROR,
            ):
                _active_skill_name = None

            # Create appropriate content based on event type
            content = event.content

            # If no content, create from payload for backward compatibility
            if content is None:
                content = self._create_content_from_event(event, content_tracking)

            # Handle private messages specially
            if event.event_type == AgentEventType.CREW_MEMBER_PRIVATE_MESSAGE:
                async for result in self._handle_private_message(
                    event, content, session_id
                ):
                    yield result
                continue

            # Mark non-skill content with skill context
            if _active_skill_name and content:
                self._mark_skill_context(content, _active_skill_name)

            # Collect main content
            if content and send_main_content_to_agent and content.is_main_content():
                _collected_main_content.append(content)

            # Create enhanced event
            enhanced_event = AgentEvent.create(
                event_type=event.event_type,
                project_name=event.project_name,
                react_type=event.react_type,
                step_id=event.step_id,
                sender_id=event.sender_id,
                sender_name=event.sender_name,
                content=content,
            )

            # Send via signals
            await self._send_event_to_signals(
                enhanced_event, crew_member, message_id, record_to_agent_history, send_main_content_to_agent
            )

            # Emit crew member activity for sidebar. Group chat uses this path; private chat
            # uses StreamEventHandler._crew_member_activity_callback. Both end at set_member_active.
            if event.event_type == AgentEventType.CREW_MEMBER_TYPING.value:
                self._signals.emit_crew_member_activity(event.sender_name, True)
            elif event.event_type == AgentEventType.CREW_MEMBER_TYPING_END.value:
                self._signals.emit_crew_member_activity(event.sender_name, False)

            # Handle crew member messages that need further processing
            if event.event_type == AgentEventType.CREW_MEMBER_MESSAGE:
                await self._handle_crew_member_message(event, content, session_id)

            yield enhanced_event

        # After streaming ends, send collected main content if requested
        if send_main_content_to_agent and _collected_main_content:
            await self._send_main_content_to_agent(
                crew_member, _collected_main_content, message_id, session_id,
                routing_depth=routing_depth,
                visited_senders=visited_senders,
            )

    def _create_content_from_event(
        self, event: "AgentEvent", content_tracking: Dict[str, str]
    ) -> Optional[StructureContent]:
        """Create StructureContent from event based on event type."""
        from agent.react import AgentEventType

        if event.event_type == AgentEventType.LLM_THINKING:
            return ThinkingContent(
                thought=event.payload.get("message", ""),
                step=event.payload.get("step"),
                total_steps=event.payload.get("total_steps"),
                title="Thinking Process",
                description="Agent's thought process"
            )

        elif event.event_type == AgentEventType.LLM_OUTPUT:
            return LlmOutputContent(
                output=event.payload.get("content", ""),
                title="LLM Output",
                description="Raw LLM output"
            )

        elif event.event_type == AgentEventType.TOOL_START:
            tool_name = event.payload.get("tool_name", "unknown")
            content = ToolCallContent(
                tool_name=tool_name,
                tool_input=event.payload.get("input", {}),
                title=f"Tool: {tool_name}",
                description="Tool execution started"
            )
            content_tracking[tool_name] = content.content_id
            return content

        elif event.event_type == AgentEventType.TOOL_PROGRESS:
            tool_name = event.payload.get("tool_name", "")
            parent_id = content_tracking.get(tool_name)
            return ProgressContent(
                progress=event.payload.get("progress", ""),
                tool_name=tool_name,
                title="Tool Execution",
                description="Tool execution in progress",
                parent_id=parent_id
            )

        elif event.event_type == AgentEventType.TOOL_END:
            tool_name = event.payload.get("tool_name", "")
            result = event.payload.get("result")
            error = event.payload.get("error")

            content = ToolResponseContent(
                tool_name=tool_name,
                result=result if not error else None,
                error=error,
                tool_status="completed" if not error else "failed",
                title=f"Tool Result: {tool_name}",
                description=f"Tool execution {'completed' if not error else 'failed'}",
                parent_id=content_tracking.get(tool_name)
            )
            if not error:
                content.complete()

            if tool_name in content_tracking:
                del content_tracking[tool_name]
            return content

        elif event.event_type == AgentEventType.FINAL:
            return TextContent(
                text=event.payload.get("final_response", ""),
                title="Response",
                description="Final response from agent"
            )

        elif event.event_type == AgentEventType.ERROR:
            return ErrorContent(
                error_message=event.payload.get("error", "Unknown error"),
                error_type=event.payload.get("error_type"),
                details=event.payload.get("details"),
                title="Error",
                description="An error occurred"
            )

        elif event.event_type == AgentEventType.TODO_WRITE:
            if event.content and isinstance(event.content, TodoWriteContent):
                return event.content
            else:
                from agent.react.todo import TodoState
                todo_dict = event.payload.get("todo", {})
                if isinstance(todo_dict, dict):
                    todo_state = TodoState.from_dict(todo_dict)
                    return TodoWriteContent.from_todo_state(
                        todo_state,
                        title="Task Progress",
                        description="Current task status"
                    )

        return None

    def _mark_skill_context(
        self, content: StructureContent, skill_name: str
    ) -> None:
        """Mark content with skill context if inside a skill execution."""
        is_skill_event = content.content_type in (
            ContentType.SKILL,
        )

        if not is_skill_event:
            if content.metadata is None:
                content.metadata = {}
            content.metadata["_skill_name"] = skill_name

    async def _send_event_to_signals(
        self,
        event: "AgentEvent",
        crew_member: "CrewMember",
        message_id: str,
        record_to_agent_history: bool,
        send_main_content_to_agent: bool,
    ) -> None:
        """Send event to AgentChatSignals."""
        from agent.filmeto_agent import FilmetoAgent

        agent_message = FilmetoAgent.convert_event_to_message(
            event,
            sender_id=crew_member.config.name,
            sender_name=crew_member.config.name.capitalize(),
            message_id=message_id
        )

        if agent_message:
            content_type_value = "text"
            if agent_message.structured_content:
                content_type_value = agent_message.structured_content[0].content_type.value

            if record_to_agent_history:
                logger.info(
                    f"Sending message: type={content_type_value}, "
                    f"id={agent_message.message_id}, sender='{agent_message.sender_id}'"
                )
                await self._signals.send_agent_message(agent_message)
            elif not send_main_content_to_agent:
                logger.debug(
                    f"Sending message (no history): type={content_type_value}, "
                    f"id={agent_message.message_id}, sender='{agent_message.sender_id}'"
                )
                agent_message.metadata = agent_message.metadata or {}
                agent_message.metadata["_no_agent_history"] = True
                await self._signals.send_agent_message(agent_message)

    async def _handle_private_message(
        self, event: "AgentEvent", content: StructureContent, session_id: str
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle private message events."""
        from agent.react import AgentEventType

        content_metadata = content.metadata if content and hasattr(content, "metadata") else {}
        message_text = content_metadata.get("message", "")
        target = content_metadata.get("target", "")
        original_sender_id = event.sender_id

        if message_text and target:
            target_member = self._crew_manager.lookup_member(target.lower())
            if target_member and target_member.config.name.lower() != original_sender_id.lower():
                logger.info(f"Sending private message from {original_sender_id} to {target}")
                cm_session_id = str(uuid.uuid4())
                async for _ in self.stream_crew_member(
                    target_member,
                    message_text,
                    plan_id=None,
                    session_id=cm_session_id,
                ):
                    pass

        yield AgentEvent.create(
            event_type=event.event_type,
            project_name=event.project_name,
            react_type=event.react_type,
            step_id=event.step_id,
            sender_id=event.sender_id,
            sender_name=event.sender_name,
            content=content,
        )

    async def _handle_crew_member_message(
        self, event: "AgentEvent", content: StructureContent, session_id: str
    ) -> None:
        """Handle crew member message events for routing."""
        from agent.react import AgentEventType

        content_metadata = content.metadata if content and hasattr(content, "metadata") else {}
        message_text = content_metadata.get("message", "")
        mode = content_metadata.get("mode", "public")
        original_sender_id = event.sender_id

        if not message_text:
            return

        cm_session_id = str(uuid.uuid4())

        if mode == "specify":
            target = content_metadata.get("target", "")
            if target:
                target_member = self._crew_manager.lookup_member(target.lower())
                if target_member and target_member.config.name.lower() != original_sender_id.lower():
                    if not (original_sender_id.lower() == PRODUCER_NAME and
                            target_member.config.name.lower() == PRODUCER_NAME):
                        logger.info(f"Routing specify message from {original_sender_id} to {target}")
                        async for _ in self.stream_crew_member(
                            target_member,
                            message_text,
                            plan_id=None,
                            session_id=cm_session_id,
                            record_to_agent_history=False,
                        ):
                            pass
        else:
            # Public mode - use LLM routing
            await self.route_message_with_llm(
                message=message_text,
                sender_id=original_sender_id,
                sender_name=original_sender_id.capitalize(),
                session_id=cm_session_id,
            )

    async def _send_main_content_to_agent(
        self,
        crew_member: "CrewMember",
        main_content: List[StructureContent],
        message_id: str,
        session_id: str,
        routing_depth: int = 0,
        visited_senders: Optional[frozenset] = None,
    ) -> None:
        """Send crew member's main content to agent for group chat routing."""
        text_parts = []
        for content in main_content:
            if isinstance(content, TextContent) and content.text:
                text_parts.append(content.text)
            elif hasattr(content, "text") and content.text:
                text_parts.append(content.text)

        if not text_parts:
            return

        combined_text = "\n\n".join(text_parts)
        sender_id = crew_member.config.name
        sender_name = crew_member.config.name.capitalize()

        logger.info(
            f"Crew member main content ready for routing: "
            f"sender={sender_id}, depth={routing_depth}, length={len(combined_text)}"
        )

        crew_member_message = AgentMessage(
            sender_id=sender_id,
            sender_name=sender_name,
            message_id=message_id,
            structured_content=main_content,
        )
        crew_member_message.metadata["session_id"] = session_id

        self._conversation_history.append(crew_member_message)
        await self._signals.send_agent_message(crew_member_message)

        # Route response: @mention fast-path first, LLM routing as fallback
        await self.route_message_with_llm(
            message=combined_text,
            sender_id=sender_id,
            sender_name=sender_name,
            session_id=session_id,
            user_message_id=message_id,
            _routing_depth=routing_depth,
            _visited_senders=visited_senders,
        )

    async def route_message_with_llm(
        self,
        message: str,
        sender_id: str,
        sender_name: str,
        session_id: str,
        user_message_id: Optional[str] = None,
        _routing_depth: int = 0,
        _visited_senders: Optional[frozenset] = None,
    ) -> None:
        """
        Route a message to appropriate crew members.

        First attempts @mention-based routing (no LLM call needed).
        Falls back to LLM routing only when no explicit @mention is found.

        Loop protection:
        - _routing_depth tracks the hop count for this routing chain.
          When it reaches MAX_ROUTING_DEPTH the chain is terminated.
        - _visited_senders accumulates sender IDs seen so far. A sender
          appearing twice signals a cycle and terminates the chain immediately.
        """
        if _visited_senders is None:
            _visited_senders = frozenset()

        # --- Loop / depth protection ---
        if _routing_depth >= MAX_ROUTING_DEPTH:
            logger.warning(
                f"Routing chain terminated: max depth {MAX_ROUTING_DEPTH} reached "
                f"(sender={sender_id}, chain={sorted(_visited_senders)})"
            )
            return

        if sender_id.lower() in {s.lower() for s in _visited_senders}:
            logger.warning(
                f"Routing cycle detected: {sender_id} already in chain "
                f"{sorted(_visited_senders)} — terminating"
            )
            return

        _visited_senders = _visited_senders | {sender_id}

        crew_members = self._crew_manager.crew_members

        if not crew_members:
            logger.warning("No crew members loaded for routing")
            producer = self._crew_manager.get_producer()
            if producer:
                async for _ in self.stream_crew_member(
                    producer, message, plan_id=None, session_id=session_id, record_to_agent_history=True
                ):
                    pass
            return

        # --- @mention-based routing (fast path, no LLM call) ---
        # Exclude the sender itself from available targets (by name and by sender_id)
        available_names = [
            name for name in crew_members
            if name.lower() != sender_id.lower()
        ]
        target = MessageTarget.parse_from_content(message, available_names)

        if target.target_type == TargetType.USER:
            logger.info(
                f"@You detected from '{sender_id}' (depth={_routing_depth}) — ending routing chain"
            )
            return

        if target.target_type == TargetType.MEMBER:
            logger.info(
                f"@mention routing: '{sender_id}' -> {target.target_names} "
                f"(depth={_routing_depth}, msg={message[:80]!r})"
            )
            decision = RoutingDecision(
                routed_members=target.target_names,
                member_messages={name: message for name in target.target_names},
            )
            if user_message_id:
                await self._emit_crew_member_read(
                    decision.routed_members, sender_id, sender_name, user_message_id, session_id
                )
            await self._dispatch_to_members(
                decision, message, session_id,
                routing_depth=_routing_depth + 1,
                visited_senders=_visited_senders,
            )
            return

        # --- LLM-based routing (no explicit @mention found) ---
        try:
            history = []
            for msg in self._conversation_history[-20:]:
                text = extract_text_content(msg)
                if text:
                    history.append({
                        "sender_id": msg.sender_id,
                        "sender_name": msg.sender_name,
                        "content": text,
                    })

            logger.info(
                f"LLM routing from '{sender_id}' (depth={_routing_depth}): {message[:100]!r}..."
            )
            decision = await self._message_router.route_message(
                message=message,
                sender_id=sender_id,
                sender_name=sender_name,
                crew_members=crew_members,
                conversation_history=history,
                max_history=20,
            )

            if not decision.routed_members:
                logger.info("No members routed for message")
                producer = self._crew_manager.get_producer()
                if producer and producer.config.name.lower() != sender_id.lower():
                    async for _ in self.stream_crew_member(
                        producer, message, plan_id=None, session_id=session_id, record_to_agent_history=True
                    ):
                        pass
                return

            logger.info(f"LLM routed to: {decision.routed_members}")

            if user_message_id and decision.routed_members:
                await self._emit_crew_member_read(
                    decision.routed_members, sender_id, sender_name, user_message_id, session_id
                )

            await self._dispatch_to_members(
                decision, message, session_id,
                routing_depth=_routing_depth + 1,
                visited_senders=_visited_senders,
            )

        except Exception as e:
            logger.error(f"Error in LLM routing: {e}", exc_info=True)
            producer = self._crew_manager.get_producer()
            if producer and producer.config.name.lower() != sender_id.lower():
                async for _ in self.stream_crew_member(
                    producer, message, plan_id=None, session_id=session_id, record_to_agent_history=True
                ):
                    pass

    async def _emit_crew_member_read(
        self,
        routed_members: List[str],
        sender_id: str,
        sender_name: str,
        user_message_id: str,
        session_id: str,
    ) -> None:
        """Emit crew_member_read event for UI read indicators."""
        crew_read_list = []
        for name in routed_members:
            member = self._crew_manager.get_member(name)
            if member:
                crew_read_list.append({
                    "id": member.config.name.lower(),
                    "name": member.config.name,
                    "icon": getattr(member.config, "icon", ""),
                    "color": getattr(member.config, "color", "#4a90e2"),
                })

        if crew_read_list:
            read_content = CrewMemberReadContent(crew_members=crew_read_list)
            read_msg = AgentMessage(
                sender_id=sender_id,
                sender_name=sender_name,
                message_id=user_message_id,
                metadata={"session_id": session_id, "event_type": "crew_member_read"},
                structured_content=[read_content],
            )
            # Record to conversation history
            self._conversation_history.append(read_msg)
            logger.debug(f"Recorded crew_member_read to history: {len(crew_read_list)} members")
            await self._signals.send_agent_message(read_msg)

    async def _dispatch_to_members(
        self,
        decision,
        message: str,
        session_id: str,
        routing_depth: int = 0,
        visited_senders: Optional[frozenset] = None,
    ) -> None:
        """Dispatch messages to routed crew members in parallel."""

        async def dispatch_to_member(member_name: str, customized_message: str):
            member = self._crew_manager.get_member(member_name)
            if not member:
                logger.warning(f"Crew member {member_name} not found")
                return

            msg_to_send = customized_message or message

            async for _ in self.stream_crew_member(
                member,
                msg_to_send,
                plan_id=None,
                session_id=session_id,
                record_to_agent_history=False,
                send_main_content_to_agent=True,
                routing_depth=routing_depth,
                visited_senders=visited_senders,
            ):
                pass

        tasks = []
        for member_name in decision.routed_members:
            customized_msg = decision.member_messages.get(member_name, message)
            tasks.append(dispatch_to_member(member_name, customized_msg))

        if tasks:
            await asyncio.gather(*tasks)
