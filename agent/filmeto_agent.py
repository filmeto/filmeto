"""
Main agent module for Filmeto application.
Implements the FilmetoAgent class with streaming capabilities.

This module now serves as the main interface, with core functionality
delegated to modules in the agent.core package.
"""
import asyncio
import logging
import uuid
from typing import AsyncIterator, AsyncGenerator, Callable, Dict, List, Optional, Any, TYPE_CHECKING

from agent.chat.agent_chat_message import AgentMessage
from agent.chat.content import (
    StructureContent, TextContent, MetadataContent, ErrorContent,
    CrewMemberReadContent
)
from agent.chat.agent_chat_types import ContentType
from agent.chat.agent_chat_signals import AgentChatSignals
from agent.chat.history.agent_chat_history_listener import AgentChatHistoryListener
from agent.plan.plan_service import PlanService
from agent.crew.crew_member import CrewMember
from agent.crew.crew_service import CrewService
from agent.router.message_router_service import MessageRouterService
from utils.path_utils import get_workspace_path
from utils.llm_utils import get_chat_service

# Import from core package
from agent.core import (
    # Instance management
    FilmetoInstanceManager,
    # Utilities
    extract_text_content,
    truncate_text,
    get_workspace_path_safe,
    get_project_from_workspace,
    resolve_project_name,
    # Constants
    PRODUCER_NAME,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_STREAMING,
)
from agent.core.filmeto_crew import FilmetoCrewManager
from agent.core.filmeto_routing import FilmetoRoutingManager
from agent.core.filmeto_plan import FilmetoPlanManager

if TYPE_CHECKING:
    from agent.event.agent_event import AgentEvent
    from agent.react.types import AgentEventType

logger = logging.getLogger(__name__)


class FilmetoAgent:
    """
    Class for managing agent capabilities in Filmeto.
    Provides streaming conversation interface and manages multiple agents.

    This is the main interface class. Core functionality is delegated to:
    - FilmetoInstanceManager: Singleton instance management (class-level)
    - FilmetoCrewManager: Crew member management
    - FilmetoRoutingManager: Message routing and streaming
    - FilmetoPlanManager: Plan operations and task execution
    """

    # ========================================================================
    # Class-level instance management (delegated to FilmetoInstanceManager)
    # ========================================================================

    @classmethod
    def get_instance(
        cls,
        workspace: Any,
        project_name: str,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        streaming: bool = DEFAULT_STREAMING,
    ) -> "FilmetoAgent":
        """Get or create a FilmetoAgent instance for the given workspace and project."""
        return FilmetoInstanceManager.get_instance(
            workspace=workspace,
            project_name=project_name,
            model=model,
            temperature=temperature,
            streaming=streaming,
        )

    @classmethod
    def remove_instance(cls, workspace: Any, project_name: str) -> bool:
        """Remove a FilmetoAgent instance from the cache."""
        return FilmetoInstanceManager.remove_instance(workspace, project_name)

    @classmethod
    def clear_all_instances(cls):
        """Clear all cached FilmetoAgent instances."""
        FilmetoInstanceManager.clear_all_instances()

    @classmethod
    def list_instances(cls) -> List[str]:
        """List all cached instance keys."""
        return FilmetoInstanceManager.list_instances()

    @classmethod
    def has_instance(cls, workspace: Any, project_name: str) -> bool:
        """Check if an instance exists for the given workspace and project."""
        return FilmetoInstanceManager.has_instance(workspace, project_name)

    # ========================================================================
    # Initialization
    # ========================================================================

    def __init__(
        self,
        workspace: Any = None,
        project: Any = None,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        streaming: bool = DEFAULT_STREAMING,
        chat_service=None,
        crew_member_service: Optional[CrewService] = None,
        plan_service: Optional[PlanService] = None,
    ):
        """Initialize the FilmetoAgent instance."""
        self.workspace = workspace
        self.project = project
        self.model = model
        self.temperature = temperature
        self.streaming = streaming

        # Core services
        self.chat_service = chat_service if chat_service else get_chat_service(workspace)
        self.crew_member_service = crew_member_service or CrewService()

        # Get project name for PlanService instance management
        project_name = resolve_project_name(self.project) or "default"
        self.plan_service = plan_service or PlanService.get_instance(workspace, project_name)

        # State
        self.conversation_history: List[AgentMessage] = []
        self.signals = AgentChatSignals()
        self._history_listener = None

        # Core managers (initialized after self is ready)
        self._crew_manager = FilmetoCrewManager(self.crew_member_service)
        self._message_router = MessageRouterService(
            chat_service=self.chat_service,
            workspace=workspace
        )
        self._routing_manager = None  # Will be initialized after _crew_manager is ready
        self._plan_manager = None  # Will be initialized after _routing_manager is ready

        # Initialize
        self._init_history_listener()
        self._init_managers()

    def _init_managers(self) -> None:
        """Initialize core managers that depend on each other."""
        # Routing manager depends on crew_manager
        self._routing_manager = FilmetoRoutingManager(
            crew_manager=self._crew_manager,
            message_router=self._message_router,
            signals=self.signals,
            conversation_history=self.conversation_history,
        )

        # Plan manager depends on routing_manager
        self._plan_manager = FilmetoPlanManager(
            plan_service=self.plan_service,
            signals=self.signals,
            routing_manager=self._routing_manager,
            resolve_project_name=lambda: resolve_project_name(self.project),
        )

    def _init_history_listener(self) -> None:
        """Initialize the history listener for persisting messages."""
        workspace_path = get_workspace_path_safe(self.workspace)
        if not workspace_path or workspace_path == "none":
            workspace_path = str(get_workspace_path())

        project_name = resolve_project_name(self.project) or "default"

        try:
            self._history_listener = AgentChatHistoryListener(
                workspace_path=workspace_path,
                project_name=project_name,
                signals=self.signals,
            )
            self._history_listener.connect()
        except Exception as e:
            logger.warning("Failed to initialize AgentChatHistoryListener: %s", e)
            self._history_listener = None

    # ========================================================================
    # Public API
    # ========================================================================

    async def chat(
        self,
        message: str,
        sender_id: str = "user",
        sender_name: str = "User",
        session_id: Optional[str] = None,
    ) -> None:
        """
        Send a message to the agents and receive responses via signals.

        This method does not return any value. Results are delivered through
        the AgentChatSignals system (send_agent_message signal).
        """
        try:
            # Ensure project is loaded
            await self._ensure_project_loaded()

            # Load crew members
            self._ensure_crew_members_loaded()

            # Create message
            initial_prompt = AgentMessage(
                sender_id=sender_id,
                sender_name=sender_name,
                structured_content=[TextContent(text=message)]
            )

            # Create or use provided session ID
            if session_id is None:
                session_id = str(uuid.uuid4())

            # Record to history
            self.conversation_history.append(initial_prompt)

            sender_type = "user" if sender_id.lower() == "user" else "crew_member"
            logger.info(f"Chat message: id={initial_prompt.message_id}, sender='{sender_id}' ({sender_type})")

            initial_prompt.metadata["session_id"] = session_id
            await self.signals.send_agent_message(initial_prompt)

            # Check for @mentions
            mentioned_member = self._crew_manager.resolve_mentioned_crew_member(message)

            if mentioned_member and mentioned_member.config.name.lower() != PRODUCER_NAME:
                await self._routing_manager._emit_crew_member_read(
                    [mentioned_member.config.name],
                    sender_id,
                    sender_name,
                    initial_prompt.message_id,
                    session_id,
                )
                async for _ in self._routing_manager.stream_crew_member(
                    mentioned_member,
                    message,
                    plan_id=None,
                    session_id=session_id,
                    record_to_agent_history=False,
                    message_sender_id=sender_id,
                    message_sender_name=sender_name,
                ):
                    pass
                return

            # No specific crew member mentioned - use LLM routing
            await self._routing_manager.route_message_with_llm(
                message=message,
                sender_id=sender_id,
                sender_name=sender_name,
                session_id=session_id,
                user_message_id=initial_prompt.message_id,
            )

        except Exception as e:
            logger.error("Exception in chat()", exc_info=True)
            async for _ in self._stream_error_message(
                f"An error occurred while processing your message: {str(e)}",
                str(uuid.uuid4()),
            ):
                pass

    async def broadcast_message(self, message: AgentMessage) -> AsyncIterator[AgentMessage]:
        """
        Broadcast a message to all agents and collect their responses.
        """
        from agent.react import AgentEventType

        for agent in self._crew_manager.crew_members.values():
            try:
                message_text = extract_text_content(message)

                async for event in agent.chat_stream(message_text, plan_id=None):
                    if event.event_type == AgentEventType.FINAL:
                        final_text = event.payload.get("final_response", "")
                        if final_text:
                            response = AgentMessage(
                                sender_id=agent.config.name,
                                sender_name=agent.config.name.capitalize(),
                                metadata={},
                                structured_content=[TextContent(text=final_text)]
                            )
                            self.conversation_history.append(response)
                            yield response
                    elif event.event_type == AgentEventType.ERROR:
                        error_text = event.payload.get("error", "Unknown error")
                        error_msg = AgentMessage(
                            sender_id=agent.config.name,
                            sender_name=agent.config.name.capitalize(),
                            metadata={},
                            structured_content=[TextContent(text=error_text)]
                        )
                        self.conversation_history.append(error_msg)
                        yield error_msg

            except Exception as e:
                error_text = f"Error in agent {agent.config.name}: {str(e)}"
                logger.error("Exception in broadcast_to_all_agents", exc_info=True)
                error_msg = AgentMessage(
                    sender_id="system",
                    sender_name="System",
                    structured_content=[TextContent(text=error_text)]
                )
                self.conversation_history.append(error_msg)
                yield error_msg

    # ========================================================================
    # Properties (delegated to managers)
    # ========================================================================

    @property
    def crew_members(self) -> Dict[str, CrewMember]:
        """Get crew members (delegated to crew manager)."""
        return self._crew_manager.crew_members

    def get_member(self, member_id: str) -> Optional[CrewMember]:
        """Get a member by ID (delegated to crew manager)."""
        return self._crew_manager.get_member(member_id)

    def list_members(self) -> List[CrewMember]:
        """List all registered members (delegated to crew manager)."""
        return self._crew_manager.list_members()

    def get_conversation_history(self) -> List[AgentMessage]:
        """Get the entire conversation history."""
        return self.conversation_history.copy()

    def clear_conversation_history(self):
        """Clear the conversation history."""
        self.conversation_history.clear()

    # ========================================================================
    # Event handling
    # ========================================================================

    async def _stream_error_message(
        self,
        message: str,
        session_id: str,
    ) -> AsyncGenerator["AgentEvent", None]:
        """Stream an error message."""
        from agent.react import AgentEvent, AgentEventType

        error_msg = AgentMessage(
            sender_id="system",
            sender_name="System",
            structured_content=[TextContent(text=message)]
        )
        logger.info(f"Sending error message: id={error_msg.message_id}, sender='system'")
        self.conversation_history.append(error_msg)
        error_msg.metadata["session_id"] = session_id
        await self.signals.send_agent_message(error_msg)

        yield AgentEvent.error(
            error_message=message,
            project_name=resolve_project_name(self.project) or "default",
            react_type="system",
            sender_id="system",
            sender_name="System",
        )

    # ========================================================================
    # Helper methods
    # ========================================================================

    async def _ensure_project_loaded(self) -> None:
        """Ensure project is loaded from workspace if not already set."""
        if not self.project and self.workspace:
            # Ensure projects are loaded in the workspace
            if hasattr(self.workspace, "project_manager") and self.workspace.project_manager:
                self.workspace.project_manager.ensure_projects_loaded()

            # Try to get the current project from workspace
            self.project = self.workspace.get_project()

            # If still no project, try to get the first available project
            if not self.project:
                project_list = self.workspace.get_projects()
                if project_list:
                    first_project_name = next(iter(project_list))
                    self.project = project_list[first_project_name]

    def _ensure_crew_members_loaded(self, refresh: bool = False) -> Dict[str, CrewMember]:
        """Ensure crew members are loaded (delegated to crew manager)."""
        return self._crew_manager.load_crew_members(self.project, refresh=refresh)

    # ========================================================================
    # Utility methods (kept as static methods for external use)
    # ========================================================================

    @staticmethod
    def convert_event_to_message(
        event: "AgentEvent",
        sender_id: str,
        sender_name: str,
        message_id: str
    ) -> Optional[AgentMessage]:
        """
        Convert an AgentEvent to an AgentMessage for UI display.
        This is the central conversion point for all event types.
        """
        # All events must have content
        if not event.content:
            raise ValueError(
                f"Event {event.event_type} must have content. "
                f"Event content cannot be None."
            )

        return AgentMessage(
            sender_id=sender_id,
            sender_name=sender_name,
            message_id=message_id,
            structured_content=[event.content]
        )

    # ========================================================================
    # Signal connections
    # ========================================================================

    def connect_message_handler(self, receiver, weak: bool = True):
        """Connect a message handler to receive agent messages."""
        self.signals.connect(receiver, weak=weak)

    def disconnect_message_handler(self, receiver):
        """Disconnect a message handler from receiving agent messages."""
        self.signals.disconnect(receiver)

    # ========================================================================
    # Context management
    # ========================================================================

    def update_context(self, project=None):
        """Update the agent context with new project information."""
        if project:
            self.project = project
            self._crew_manager.load_crew_members(project, refresh=True)
