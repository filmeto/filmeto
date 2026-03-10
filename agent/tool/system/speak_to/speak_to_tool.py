"""SpeakTo tool for crew member communication."""
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING, AsyncGenerator
import logging
import uuid

from ...base_tool import BaseTool, ToolMetadata, ToolParameter
from agent.event.agent_event import AgentEvent, AgentEventType
from agent.chat.agent_chat_message import AgentMessage
from agent.chat.content import TextContent

# Tool directory for metadata loading
_tool_dir = Path(__file__).parent

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ....tool_context import ToolContext


class SpeakToTool(BaseTool):
    """
    Tool for crew member communication in the Filmeto project.

    This tool supports three communication modes:
    - public: Send message to FilmetoAgent, visible to all in history timeline
    - specify: Send message with @mention, visible to all, typically handled by mentioned member
    - private: Send message directly to a specific crew member, not recorded in history

    For public and specify modes, the tool directly calls FilmetoAgent.chat() to ensure
    proper history recording and message routing.
    """

    def __init__(self):
        super().__init__(
            name="speak_to",
            description="Send messages between crew members with different visibility modes: public, specify, private"
        )
        # Set tool directory for metadata loading from tool.md
        self._tool_dir = _tool_dir

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional["ToolContext"] = None,
        project_name: str = "",
        react_type: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
        message_id: str = "",
    ) -> AsyncGenerator["AgentEvent", None]:
        """
        Execute the speak_to tool asynchronously.

        Args:
            parameters: Dictionary containing:
                - mode (str): Communication mode - "public", "specify", or "private"
                - message (str): The message content to send
                - target (str, optional): Target crew member name (required for "specify" and "private" modes)
            context: ToolContext containing workspace and project info
            project_name: Project name for event tracking
            react_type: React type for event tracking
            step_id: Step ID for event tracking
            sender_id: ID of the event sender (the crew member sending the message)
            sender_name: Display name of the event sender

        Yields:
            AgentEvent objects with progress updates and results
        """
        try:
            mode = parameters.get("mode", "public").lower()
            message = parameters.get("message", "")
            target = parameters.get("target", "")

            if not message:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,                    step_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    error="message parameter is required"
                )
                return

            # Validate mode
            valid_modes = ["public", "specify", "private"]
            if mode not in valid_modes:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,                    step_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    error=f"Invalid mode '{mode}'. Valid modes: {', '.join(valid_modes)}"
                )
                return

            # Validate target for specify and private modes
            if mode in ["specify", "private"] and not target:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,                    step_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    error=f"target parameter is required for '{mode}' mode"
                )
                return

            # Route to appropriate handler
            if mode == "public":
                async for event in self._handle_public(
                    message, sender_id, sender_name, context,
                    project_name, react_type, step_id
                ):
                    yield event
            elif mode == "specify":
                async for event in self._handle_specify(
                    message, target, sender_id, sender_name, context,
                    project_name, react_type, step_id
                ):
                    yield event
            elif mode == "private":
                async for event in self._handle_private(
                    message, target, sender_id, sender_name, context,
                    project_name, react_type, step_id
                ):
                    yield event

        except Exception as e:
            logger.error(f"Error in speak_to tool: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,                step_id,
                sender_id=sender_id,
                sender_name=sender_name,
                error=str(e)
            )

    def _get_filmeto_agent(self, context: Optional["ToolContext"]):
        """Get FilmetoAgent instance from context."""
        if context and hasattr(context, 'workspace') and hasattr(context, 'project_name'):
            from agent.filmeto_agent import FilmetoAgent
            return FilmetoAgent.get_instance(
                workspace=context.workspace,
                project_name=context.project_name,
            )
        return None

    async def _handle_public(
        self,
        message: str,
        sender_id: str,
        sender_name: str,
        context: Optional["ToolContext"],
        project_name: str,
        react_type: str,        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """
        Handle public mode: send message directly to FilmetoAgent.chat().

        The message will be recorded in agent history and processed by
        FilmetoAgent's LLM routing logic for intelligent multi-member routing.
        """
        # Emit progress event
        yield self._create_event(
            "tool_progress",
            project_name,
            react_type,            step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            progress=f"Sending public message from {sender_name}"
        )

        message_id = str(uuid.uuid4())

        # Get FilmetoAgent and call chat() directly
        agent = self._get_filmeto_agent(context)
        if agent:
            logger.info(f"📤 speak_to (public): {sender_name} -> FilmetoAgent, message_id={message_id[:8]}...")
            # Call chat() with crew member as sender
            await agent.chat(
                message=message,
                sender_id=sender_id,
                sender_name=sender_name,
            )
        else:
            logger.warning(f"Could not get FilmetoAgent instance for speak_to public mode")

        # Emit tool end event
        yield self._create_event(
            "tool_end",
            project_name,
            react_type,            step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            ok=True,
            result={
                "mode": "public",
                "success": True,
                "message": f"Public message sent from {sender_name}",
                "message_id": message_id
            }
        )

    async def _handle_specify(
        self,
        message: str,
        target: str,
        sender_id: str,
        sender_name: str,
        context: Optional["ToolContext"],
        project_name: str,
        react_type: str,        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """
        Handle specify mode: send message with @mention directly to FilmetoAgent.chat().

        The message will start with @target and be processed by FilmetoAgent's
        routing logic, typically routed to the mentioned crew member.
        """
        # Emit progress event
        yield self._create_event(
            "tool_progress",
            project_name,
            react_type,            step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            progress=f"Sending message from {sender_name} to @{target}"
        )

        # Format message with @mention
        formatted_message = f"@{target} {message}"
        message_id = str(uuid.uuid4())

        # Get FilmetoAgent and call chat() directly
        agent = self._get_filmeto_agent(context)
        if agent:
            logger.info(f"📤 speak_to (specify): {sender_name} -> @{target}, message_id={message_id[:8]}...")
            # Call chat() with crew member as sender and @mention in message
            await agent.chat(
                message=formatted_message,
                sender_id=sender_id,
                sender_name=sender_name,
            )
        else:
            logger.warning(f"Could not get FilmetoAgent instance for speak_to specify mode")

        # Emit tool end event
        yield self._create_event(
            "tool_end",
            project_name,
            react_type,            step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            ok=True,
            result={
                "mode": "specify",
                "success": True,
                "target": target,
                "message": f"Message sent from {sender_name} to @{target}",
                "message_id": message_id
            }
        )

    async def _handle_private(
        self,
        message: str,
        target: str,
        sender_id: str,
        sender_name: str,
        context: Optional["ToolContext"],
        project_name: str,
        react_type: str,        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """
        Handle private mode: send message directly to target via event.

        Private messages are NOT recorded in agent history and are sent
        directly to the target crew member.
        """
        # Emit progress event
        yield self._create_event(
            "tool_progress",
            project_name,
            react_type,            step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            progress=f"Sending private message from {sender_name} to {target}"
        )

        message_id = str(uuid.uuid4())

        # Create event for direct delivery - NOT processed through agent routing
        # and NOT recorded to history
        text_content = TextContent(
            text=message,
            title=f"Private message from {sender_name}",
            description=f"Private message to {target}"
        )
        # Store routing metadata in content
        text_content.metadata = {
            "mode": "private",
            "message": message,
            "target": target,
            "message_id": message_id,
            "record_to_history": False,
            "process_through_agent": False,
        }

        yield AgentEvent.create(
            event_type="crew_member_private_message",
            project_name=project_name,
            react_type=react_type,            step_id=step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=text_content
        )

        # Emit tool end event
        yield self._create_event(
            "tool_end",
            project_name,
            react_type,            step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            ok=True,
            result={
                "mode": "private",
                "success": True,
                "target": target,
                "message": f"Private message sent from {sender_name} to {target}",
                "message_id": message_id
            }
        )
