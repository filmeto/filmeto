"""
Main agent module for Filmeto application.
Implements the FilmetoAgent class with streaming capabilities.
"""
import json
import logging
import re
import uuid
from typing import AsyncIterator, AsyncGenerator, Callable, Dict, List, Optional, Any, TYPE_CHECKING
from agent.chat.agent_chat_message import AgentMessage
from agent.chat.content import (
    StructureContent, TextContent, ThinkingContent, ToolCallContent,
    ToolResponseContent, ProgressContent, MetadataContent, ErrorContent,
    LlmOutputContent, TodoWriteContent, create_content
)
from agent.chat.agent_chat_types import ContentType
from agent.chat.agent_chat_signals import AgentChatSignals
from agent.chat.history.agent_chat_history_listener import AgentChatHistoryListener
from agent.llm.llm_service import LlmService
from agent.plan.plan_models import Plan, PlanInstance, PlanTask, TaskStatus
from agent.plan.plan_service import PlanService
from agent.crew.crew_member import CrewMember
from agent.crew.crew_title import sort_crew_members_by_title_importance
from agent.crew.crew_service import CrewService
from utils.path_utils import get_workspace_path

if TYPE_CHECKING:
    from agent.event.agent_event import AgentEvent
    from agent.react.types import AgentEventType

logger = logging.getLogger(__name__)


# Pattern for @mentions supporting multiple languages including Chinese, Japanese, Korean, etc.
# Matches: letters, numbers, underscores, hyphens, and CJK characters (Chinese, Japanese, Korean)
# Examples: @director, @导演, @ cinematographer, @分镜师
_MENTION_PATTERN = re.compile(r"@([\w\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af_-]+)")
_PRODUCER_NAME = "producer"


def _extract_text_content(message: AgentMessage) -> str:
    """Extract text content from a message's structured_content."""
    if not message.structured_content:
        return ""
    for sc in message.structured_content:
        if sc.content_type == ContentType.TEXT and isinstance(sc, TextContent):
            return sc.text
    return ""




class FilmetoAgent:
    """
    Class for managing agent capabilities in Filmeto.
    Provides streaming conversation interface and manages multiple agents.

    Instances are managed statically and can be retrieved using get_instance().
    """

    # Class-level instance storage: dict[(workspace_path, project_name)] -> FilmetoAgent
    _instances: Dict[str, 'FilmetoAgent'] = {}
    _lock = False  # Simple lock for thread safety (can be replaced with threading.Lock if needed)

    def __init__(
        self,
        workspace: Any = None,
        project: Any = None,
        model='gpt-4o-mini',
        temperature=0.7,
        streaming=True,
        llm_service: Optional[LlmService] = None,
        crew_member_service: Optional[CrewService] = None,
        plan_service: Optional[PlanService] = None,
    ):
        """Initialize the FilmetoAgent instance."""
        self.workspace = workspace
        self.project = project
        self.model = model
        self.temperature = temperature
        self.streaming = streaming
        self.members: Dict[str, CrewMember] = {}
        self.conversation_history: List[AgentMessage] = []
        self.llm_service = llm_service or LlmService(workspace)
        self.crew_member_service = crew_member_service or CrewService()

        # Get project name for PlanService instance management
        project_name = self._resolve_project_name() or "default"
        self.plan_service = plan_service or PlanService.get_instance(workspace, project_name)
        self.crew_members: Dict[str, CrewMember] = {}
        self._crew_member_lookup: Dict[str, CrewMember] = {}
        self.signals = AgentChatSignals()
        self._history_listener = None
        self._init_history_listener()

        # Initialize the agent
        self._init_agent()
        # Note: _ensure_crew_members_loaded will be called in the chat method when needed

    @classmethod
    def get_instance(
        cls,
        workspace: Any,
        project_name: str,
        model: str = 'gpt-4o-mini',
        temperature: float = 0.7,
        streaming: bool = True,
    ) -> 'FilmetoAgent':
        """
        Get or create a FilmetoAgent instance for the given workspace and project.

        Each unique (workspace_path, project_name) combination gets its own instance
        that will be reused across multiple calls.

        Args:
            workspace: The workspace object
            project_name: The name of the project
            model: The LLM model to use (only used when creating new instance)
            temperature: The temperature setting (only used when creating new instance)
            streaming: Whether to use streaming (only used when creating new instance)

        Returns:
            FilmetoAgent: The agent instance for this workspace/project combination
        """
        # Extract workspace path for key generation
        workspace_path = cls._get_workspace_path(workspace)

        # Create instance key
        instance_key = f"{workspace_path}:{project_name}"

        # Check if instance already exists
        if instance_key in cls._instances:
            logger.debug(f"Reusing existing FilmetoAgent instance for {instance_key}")
            return cls._instances[instance_key]

        # Create new instance
        logger.info(f"Creating new FilmetoAgent instance for {instance_key}")

        # Get project object from workspace
        project = cls._get_project_from_workspace(workspace, project_name)

        agent = cls(
            workspace=workspace,
            project=project,
            model=model,
            temperature=temperature,
            streaming=streaming,
        )

        # Store instance
        cls._instances[instance_key] = agent
        return agent

    @classmethod
    def remove_instance(cls, workspace: Any, project_name: str) -> bool:
        """
        Remove a FilmetoAgent instance from the cache.

        Args:
            workspace: The workspace object
            project_name: The name of the project

        Returns:
            bool: True if instance was removed, False if it didn't exist
        """
        workspace_path = cls._get_workspace_path(workspace)
        instance_key = f"{workspace_path}:{project_name}"

        if instance_key in cls._instances:
            del cls._instances[instance_key]
            logger.info(f"Removed FilmetoAgent instance for {instance_key}")
            return True
        return False

    @classmethod
    def clear_all_instances(cls):
        """Clear all cached FilmetoAgent instances."""
        count = len(cls._instances)
        cls._instances.clear()
        logger.info(f"Cleared {count} FilmetoAgent instance(s)")

    @classmethod
    def list_instances(cls) -> List[str]:
        """
        List all cached instance keys.

        Returns:
            List of instance keys in format "workspace_path:project_name"
        """
        return list(cls._instances.keys())

    @classmethod
    def has_instance(cls, workspace: Any, project_name: str) -> bool:
        """
        Check if an instance exists for the given workspace and project.

        Args:
            workspace: The workspace object
            project_name: The name of the project

        Returns:
            bool: True if instance exists, False otherwise
        """
        workspace_path = cls._get_workspace_path(workspace)
        instance_key = f"{workspace_path}:{project_name}"
        return instance_key in cls._instances

    @staticmethod
    def _get_workspace_path(workspace: Any) -> str:
        """Extract workspace path from workspace object."""
        if workspace is None:
            return "none"
        if hasattr(workspace, 'workspace_path'):
            return workspace.workspace_path
        if hasattr(workspace, 'path'):
            return str(workspace.path)
        return str(id(workspace))

    @staticmethod
    def _get_project_from_workspace(workspace: Any, project_name: str) -> Any:
        """Get project object from workspace by name."""
        if workspace is None:
            return None

        # Try to get project by name
        if hasattr(workspace, 'get_project'):
            # First try to get current project
            project = workspace.get_project()
            if project:
                # Check if it matches the requested name
                proj_name = None
                if hasattr(project, 'project_name'):
                    proj_name = project.project_name
                elif hasattr(project, 'name'):
                    proj_name = project.name
                elif isinstance(project, str):
                    proj_name = project

                if proj_name == project_name:
                    return project

        # Try to get from project manager
        if hasattr(workspace, 'project_manager') and workspace.project_manager:
            if hasattr(workspace.project_manager, 'ensure_projects_loaded'):
                workspace.project_manager.ensure_projects_loaded()

            if hasattr(workspace, 'get_projects'):
                projects = workspace.get_projects()
                if projects and project_name in projects:
                    return projects[project_name]

        # Fallback: return None and let agent handle it
        return None
    
    def _init_agent(self):
        """Initialize the agent using LlmService."""
        # Check if the LLM service is properly configured
        if self.llm_service and self.llm_service.validate_config():
            # Agent is properly configured
            pass
        else:
            # Agent not configured due to missing API key or base URL
            pass

    def _init_history_listener(self) -> None:
        workspace_path = None
        if self.workspace is not None:
            if hasattr(self.workspace, "workspace_path"):
                workspace_path = self.workspace.workspace_path
            elif hasattr(self.workspace, "path"):
                workspace_path = str(self.workspace.path)
            elif isinstance(self.workspace, str):
                workspace_path = self.workspace

        if not workspace_path:
            workspace_path = str(get_workspace_path())

        project_name = self._resolve_project_name() or "default"

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

    def _convert_event_to_message(
        self,
        event: 'AgentEvent',
        sender_id: str,
        sender_name: str,
        message_id: str
    ) -> Optional[AgentMessage]:
        """
        Convert an AgentEvent to an AgentMessage for UI display.
        This is the central conversion point for all event types.

        Args:
            event: The AgentEvent to convert (must have content field populated)
            sender_id: ID of the message sender
            sender_name: Display name of the sender
            message_id: Message ID to use

        Returns:
            AgentMessage if conversion successful, None otherwise

        Raises:
            ValueError: If event.content is None
        """
        from agent.react import AgentEventType

        # All events must have content now
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
    
    def register_agent(self, agent_id: str, name: str, role_description: str, handler_func: Callable):
        """
        Register a new agent with a specific role.
        This method is deprecated since we're moving to direct CrewMember usage.
        Use _register_crew_member instead which directly adds CrewMembers to members dict.

        Args:
            agent_id: Unique identifier for the agent
            name: Display name for the agent
            role_description: Description of the agent's role
            handler_func: Async function that handles messages and yields responses
        """
        # Create a minimal CrewMember-like object for backward compatibility
        from unittest.mock import Mock
        mock_config = Mock()
        mock_config.name = name
        mock_config.description = role_description

        mock_agent = Mock()
        mock_agent.config = mock_config
        mock_agent.chat_stream = handler_func

        self.members[agent_id] = mock_agent

    def get_member(self, member_id: str) -> Optional[CrewMember]:
        """Get a member by ID."""
        return self.members.get(member_id)

    def list_members(self) -> List[CrewMember]:
        """List all registered members, sorted by crew title importance."""
        return sort_crew_members_by_title_importance(list(self.members.values()))

    def _ensure_crew_members_loaded(self, refresh: bool = False) -> Dict[str, CrewMember]:
        if not self.project:
            self.crew_members = {}
            self._crew_member_lookup = {}
            return {}

        crew_members = self.crew_member_service.load_project_crew_members(self.project, refresh=refresh)
        self.crew_members = crew_members
        # Create lookup with name, crew_title, and display_names as keys
        self._crew_member_lookup = {}
        for name, agent in crew_members.items():
            # Add the agent by its name (current behavior)
            self._crew_member_lookup[name.lower()] = agent

            # Add the agent by its crew title (if available in metadata)
            crew_title = agent.config.metadata.get('crew_title')
            if crew_title:
                self._crew_member_lookup[crew_title.lower()] = agent

                # Also add display names (localized titles) for mention matching
                # This allows mentioning by localized title like @导演, @分镜师, etc.
                from agent.crew.crew_title import CrewTitle
                title_instance = CrewTitle.create_from_title(crew_title)
                if title_instance:
                    # Get display name in current language
                    display_name = title_instance.get_title_display()
                    if display_name and display_name != title_instance.title:
                        self._crew_member_lookup[display_name] = agent

                    # Also add all available display names for cross-language mentions
                    if title_instance.display_names:
                        for lang, lang_display_name in title_instance.display_names.items():
                            if lang_display_name and lang_display_name not in self._crew_member_lookup:
                                self._crew_member_lookup[lang_display_name] = agent

        for crew_member in crew_members.values():
            self._register_crew_member(crew_member)

        return crew_members

    def _register_crew_member(self, crew_member: CrewMember) -> None:
        # Directly add the CrewMember to the members dictionary
        self.members[crew_member.config.name] = crew_member

    def _extract_mentions(self, content: str) -> List[str]:
        if not content:
            return []
        return [match.group(1) for match in _MENTION_PATTERN.finditer(content)]

    def _resolve_mentioned_crew_member(self, content: str) -> Optional[CrewMember]:
        for mention in self._extract_mentions(content):
            candidate = mention.lower()
            crew_member = self._crew_member_lookup.get(candidate)
            if crew_member:
                return crew_member
        return None

    def _resolve_mentioned_title(self, content: str) -> Optional[CrewMember]:
        """Resolve a crew member by @mention (supports multilingual titles)."""
        for mention in self._extract_mentions(content):
            # Direct lookup in _crew_member_lookup which now contains:
            # - agent name
            # - crew_title (e.g., "director")
            # - display_name in current language (e.g., "导演")
            # - all display_names from metadata
            crew_member = self._crew_member_lookup.get(mention)
            if crew_member:
                return crew_member

            # Fallback: try case-insensitive match for display names
            mention_lower = mention.lower()
            for key, agent in self._crew_member_lookup.items():
                if key.lower() == mention_lower:
                    return agent

        return None

    def _get_producer_crew_member(self) -> Optional[CrewMember]:
        return self._crew_member_lookup.get(_PRODUCER_NAME)

    def _resolve_project_name(self) -> Optional[str]:
        project = self.project
        if project is None:
            return None
        if hasattr(project, "project_name"):
            return project.project_name
        if hasattr(project, "name"):
            return project.name
        if isinstance(project, str):
            return project
        return None

    def _truncate_text(self, text: str, limit: int = 160) -> str:
        if text is None:
            return ""
        text = text.strip()
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    async def _emit_system_event(
        self,
        event_type: str,
        session_id: str,
        sender_id: Optional[str] = None,
        sender_name: Optional[str] = None,
        message_id: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """Emit a system event via AgentChatSignals for UI feedback.

        Args:
            event_type: Type of the event
            session_id: Session identifier
            sender_id: Optional sender ID (defaults to "system")
            sender_name: Optional sender name (defaults to "System")
            message_id: Optional message ID to reuse (for crew member message chaining)
            **kwargs: Additional event metadata
        """
        # Default to system if no sender provided
        if sender_id is None:
            sender_id = "system"
        if sender_name is None:
            sender_name = "System"

        meta = {"event_type": event_type, "session_id": session_id, **kwargs}
        msg = AgentMessage(
            sender_id=sender_id,
            sender_name=sender_name,
            metadata=meta,
            message_id=message_id if message_id else str(uuid.uuid4()),
            structured_content=[MetadataContent(
                metadata_type=event_type,
                metadata_data={"event_type": event_type, **kwargs},
                title=event_type,
                description="",
            )],
        )
        await self.signals.send_agent_message(msg)

    def _build_producer_message(self, user_message: str, plan_id: str, retry: bool = False) -> str:
        """
        Build a message for the producer agent.
        The producer will use its ReAct loop to determine how to respond to the user message,
        including whether to create a plan, delegate to other crew members, or provide a direct response.
        """
        return "\n".join([
            f"User message: {user_message}",
            f"Current plan id: {plan_id}",
            "Please process this message appropriately using your skills and judgment.",
            "If a plan needs to be created or updated, use the appropriate planning skills.",
            "If other crew members should handle this, delegate appropriately.",
            "Provide a helpful response to the user."
        ])

    def _build_task_message(self, task: PlanTask, plan_id: str) -> str:
        parameters = json.dumps(task.parameters or {}, ensure_ascii=True)
        needs = ", ".join(task.needs) if task.needs else "none"
        return "\n".join([
            f"@{task.title}",
            f"Plan id: {plan_id}",
            f"Task id: {task.id}",
            f"Task name: {task.name}",
            f"Task description: {task.description}",
            f"Dependencies: {needs}",
            f"Parameters: {parameters}",
            "Respond with your output. If needed, update the plan with plan_update.",
        ])

    def _create_plan(self, project_name: str, user_message: str) -> Optional[Plan]:
        if not project_name:
            return None
        name = "Producer Plan"
        description = self._truncate_text(user_message)
        metadata = {"source": _PRODUCER_NAME, "request": user_message}
        return self.plan_service.create_plan(
            project_name=project_name,
            name=name,
            description=description,
            tasks=[],
            metadata=metadata,
        )

    def _producer_response_has_error(self, response: Optional[str]) -> bool:
        if not response:
            return False
        lowered = response.lower()
        return "llm service is not configured" in lowered or "error calling llm" in lowered

    def _dependencies_satisfied(self, plan_instance: PlanInstance, task: PlanTask) -> bool:
        if not task.needs:
            return True
        for dependency_id in task.needs:
            dependency = next((t for t in plan_instance.tasks if t.id == dependency_id), None)
            if not dependency or dependency.status != TaskStatus.COMPLETED:
                return False
        return True

    def _get_ready_tasks(self, plan_instance: PlanInstance) -> List[PlanTask]:
        ready = []
        for task in plan_instance.tasks:
            if task.status not in {TaskStatus.CREATED, TaskStatus.READY}:
                continue
            if self._dependencies_satisfied(plan_instance, task):
                ready.append(task)
        return ready

    def _has_incomplete_tasks(self, plan_instance: PlanInstance) -> bool:
        for task in plan_instance.tasks:
            if task.status not in {TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED}:
                return True
        return False

    async def _stream_agent_messages(
        self,
        responses: AsyncIterator[AgentMessage],
        session_id: str,
    ) -> AsyncGenerator["AgentEvent", None]:
        from agent.react import AgentEvent, AgentEventType

        async for response in responses:
            self.conversation_history.append(response)
            response.metadata["session_id"] = session_id
            await self.signals.send_agent_message(response)

            # Convert AgentMessage to ReactEvent for upstream consumption
            # Check content type from structured_content
            response_content_type = ContentType.TEXT  # Default
            if response.structured_content:
                response_content_type = response.structured_content[0].content_type

            if response_content_type == ContentType.TEXT:
                yield AgentEvent.final(
                    final_response=_extract_text_content(response),
                    project_name=self._resolve_project_name() or "default",
                    react_type=response.sender_id,
                    run_id=getattr(self, "_run_id", ""),
                    sender_id=response.sender_id,
                    sender_name=response.sender_name,
                )
            elif response_content_type == ContentType.ERROR:
                yield AgentEvent.error(
                    error_message=_extract_text_content(response),
                    project_name=self._resolve_project_name() or "default",
                    react_type=response.sender_id,
                    run_id=getattr(self, "_run_id", ""),
                    sender_id=response.sender_id,
                    sender_name=response.sender_name,
                )

    async def _stream_crew_member(
        self,
        crew_member: CrewMember,
        message: str,
        plan_id: Optional[str],
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        message_id: Optional[str] = None,
    ) -> AsyncGenerator["AgentEvent", None]:
        from agent.react import AgentEvent, AgentEventType

        # Set the current message ID on the crew member for content tracking
        # Use provided message_id or generate a new one
        if message_id is None:
            message_id = str(uuid.uuid4())
        crew_member._current_message_id = message_id

        # Track content IDs for hierarchical relationships (e.g., tool → progress updates)
        content_tracking: Dict[str, str] = {}  # tool_name → content_id mapping

        # Track active skill execution for marking child content with skill context.
        # Events between SKILL_START and SKILL_END/SKILL_ERROR get metadata marking
        # so that history loading can associate them as skill children.
        _active_skill_name: Optional[str] = None
        _active_skill_run_id: Optional[str] = None

        async for event in crew_member.chat_stream(message, plan_id=plan_id):
            # Add metadata to the event payload (kept for backward compatibility during transition)
            event_payload = dict(event.payload)
            if metadata:
                event_payload.update(metadata)
            if plan_id:
                event_payload["plan_id"] = plan_id

            # Track skill execution boundaries
            if event.event_type in (AgentEventType.SKILL_START.value, AgentEventType.SKILL_START):
                if event.content and hasattr(event.content, 'skill_name'):
                    _active_skill_name = event.content.skill_name
                    _active_skill_run_id = getattr(event.content, 'run_id', '') or event.run_id
            elif event.event_type in (
                AgentEventType.SKILL_END.value, AgentEventType.SKILL_END,
                AgentEventType.SKILL_ERROR.value, AgentEventType.SKILL_ERROR,
            ):
                _active_skill_name = None
                _active_skill_run_id = None

            # Create appropriate content based on event type
            # First, check if event already has content (from react.py)
            content = event.content

            # If no content, create from payload for backward compatibility
            if content is None:
                if event.event_type == AgentEventType.LLM_THINKING:
                    # Create ThinkingContent
                    content = ThinkingContent(
                        thought=event.payload.get("message", ""),
                        step=event.payload.get("step"),
                        total_steps=event.payload.get("total_steps"),
                        title="Thinking Process",
                        description="Agent's thought process"
                    )

                elif event.event_type == AgentEventType.LLM_OUTPUT:
                    # Create LlmOutputContent for LLM output
                    content = LlmOutputContent(
                        output=event.payload.get("content", ""),
                        title="LLM Output",
                        description="Raw LLM output"
                    )

                elif event.event_type == AgentEventType.TOOL_START:
                    # Create ToolCallContent and track it
                    tool_name = event.payload.get("tool_name", "unknown")
                    content = ToolCallContent(
                        tool_name=tool_name,
                        tool_input=event.payload.get("input", {}),
                        title=f"Tool: {tool_name}",
                        description="Tool execution started"
                    )
                    content_tracking[tool_name] = content.content_id

                elif event.event_type == AgentEventType.TOOL_PROGRESS:
                    # Create ProgressContent with parent reference
                    tool_name = event.payload.get("tool_name", "")
                    parent_id = content_tracking.get(tool_name)
                    content = ProgressContent(
                        progress=event.payload.get("progress", ""),
                        tool_name=tool_name,
                        title="Tool Execution",
                        description="Tool execution in progress",
                        parent_id=parent_id
                    )

                elif event.event_type == AgentEventType.TOOL_END:
                    # Create ToolResponseContent and mark as completed
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
                    content.complete()

                    # Clean up tracking
                    if tool_name in content_tracking:
                        del content_tracking[tool_name]

                elif event.event_type == AgentEventType.FINAL:
                    # Create TextContent for final response
                    final_text = event.payload.get("final_response", "")
                    content = TextContent(
                        text=final_text,
                        title="Response",
                        description="Final response from agent"
                    )

                elif event.event_type == AgentEventType.ERROR:
                    # Create ErrorContent
                    content = ErrorContent(
                        error_message=event.payload.get("error", "Unknown error"),
                        error_type=event.payload.get("error_type"),
                        details=event.payload.get("details"),
                        title="Error",
                        description="An error occurred"
                    )

                elif event.event_type == AgentEventType.TODO_WRITE:
                    # Create TodoWriteContent from event content or payload
                    if event.content and isinstance(event.content, TodoWriteContent):
                        content = event.content
                    else:
                        # Fallback: create from payload (backward compatibility)
                        from agent.react.todo import TodoState
                        todo_dict = event.payload.get("todo", {})
                        if isinstance(todo_dict, dict):
                            todo_state = TodoState.from_dict(todo_dict)
                            content = TodoWriteContent.from_todo_state(
                                todo_state,
                                title="Task Progress",
                                description="Current task status"
                            )
                        else:
                            # Fallback to MetadataContent for compatibility
                            content = MetadataContent(
                                metadata_type="todo_write",
                                metadata_data=event.payload.get("todo", {}),
                                title="Task Update",
                                description="Task list has been updated"
                            )

            # Mark non-skill content with skill context if inside a skill execution.
            # This metadata is used during history loading to associate content
            # (thinking, llm_output, tool_call, etc.) as children of the enclosing skill.
            if _active_skill_name and content:
                is_skill_event = event.event_type in (
                    AgentEventType.SKILL_START.value, AgentEventType.SKILL_START,
                    AgentEventType.SKILL_PROGRESS.value, AgentEventType.SKILL_PROGRESS,
                    AgentEventType.SKILL_END.value, AgentEventType.SKILL_END,
                    AgentEventType.SKILL_ERROR.value, AgentEventType.SKILL_ERROR,
                )
                if not is_skill_event:
                    if content.metadata is None:
                        content.metadata = {}
                    content.metadata['_skill_name'] = _active_skill_name
                    if _active_skill_run_id:
                        content.metadata['_skill_run_id'] = _active_skill_run_id

            # Create enhanced event with content
            enhanced_event = AgentEvent.create(
                event_type=event.event_type,
                project_name=event.project_name,
                react_type=event.react_type,
                run_id=event.run_id,
                step_id=event.step_id,
                sender_id=event.sender_id,
                sender_name=event.sender_name,
                content=content,
            )

            # Convert event to message and send via AgentChatSignals
            agent_message = self._convert_event_to_message(
                enhanced_event,
                sender_id=crew_member.config.name,
                sender_name=crew_member.config.name.capitalize(),
                message_id=message_id
            )

            if agent_message:
                # Derive content type for logging
                content_type_value = "text"
                if agent_message.structured_content:
                    content_type_value = agent_message.structured_content[0].content_type.value

                logger.info(
                    f"📤 Sending message: type={content_type_value}, "
                    f"id={agent_message.message_id}, sender='{agent_message.sender_id}', "
                    f"content_id={enhanced_event.content.content_id if enhanced_event.content else 'N/A'}"
                )
                await self.signals.send_agent_message(agent_message)

            # Yield the event for upstream
            try:
                yield enhanced_event
            except Exception as e:
                logger.error(f"❌ Exception in _stream_crew_member while yielding event", exc_info=True)
                # Continue processing despite the yield error

    async def _stream_error_message(
        self,
        message: str,
        session_id: str,
    ) -> AsyncGenerator["AgentEvent", None]:
        from agent.react import AgentEvent, AgentEventType

        error_msg = AgentMessage(
            sender_id="system",
            sender_name="System",
            structured_content=[TextContent(text=message)]
        )
        logger.info(f"❌ Sending error message: id={error_msg.message_id}, sender='system', content_preview='{message[:50]}{'...' if len(message) > 50 else ''}'")
        self.conversation_history.append(error_msg)
        error_msg.metadata["session_id"] = session_id
        await self.signals.send_agent_message(error_msg)

        # Also yield as ReactEvent
        yield AgentEvent.error(
            error_message=message,
            project_name=self._resolve_project_name() or "default",
            react_type="system",
            run_id=getattr(self, "_run_id", ""),
            sender_id="system",
            sender_name="System",
        )

    async def chat(self, message: str) -> None:
        """
        Send a message to the agents and receive responses via signals.

        This method does not return any value. Results are delivered through
        the AgentChatSignals system (send_agent_message signal).

        Args:
            message: The message to process
        """
        try:
            # Ensure project is loaded if not provided but workspace exists
            if not self.project and self.workspace:
                # Ensure projects are loaded in the workspace
                if hasattr(self.workspace, 'project_manager') and self.workspace.project_manager:
                    self.workspace.project_manager.ensure_projects_loaded()

                # Try to get the current project from workspace
                self.project = self.workspace.get_project()

                # If still no project, try to get the first available project
                if not self.project:
                    project_list = self.workspace.get_projects()
                    if project_list:
                        # Use the first project in the list as default
                        first_project_name = next(iter(project_list))
                        self.project = project_list[first_project_name]

            # Create an AgentMessage from the string
            from agent.chat.content import TextContent
            initial_prompt = AgentMessage(
                sender_id="user",
                sender_name="User",
                structured_content=[TextContent(text=message)]
            )
            logger.info(f"📥 Created initial prompt message: id={initial_prompt.message_id}, sender='user', content_preview='{message[:50]}{'...' if len(message) > 50 else ''}'")

            # Create a unique session ID for this conversation
            session_id = str(uuid.uuid4())

            # Add the initial prompt to history
            self.conversation_history.append(initial_prompt)

            initial_prompt.metadata["session_id"] = session_id
            await self.signals.send_agent_message(initial_prompt)

            self._ensure_crew_members_loaded()

            # Check for @mentions by name or title - if found, route directly to that crew member
            # This prevents producer from intervening when a specific crew member is mentioned
            mentioned_crew_member = self._resolve_mentioned_crew_member(message)
            mentioned_agent_by_title = self._resolve_mentioned_title(message)

            # Use the found crew member (by name takes priority over title)
            target_crew_member = mentioned_crew_member or mentioned_agent_by_title

            if target_crew_member and target_crew_member.config.name.lower() != _PRODUCER_NAME:
                await self._emit_system_event(
                    "crew_member_start",
                    session_id,
                    sender_id=target_crew_member.config.name,
                    sender_name=target_crew_member.config.name,
                    crew_member_name=target_crew_member.config.name,
                    message=message,
                )
                async for _ in self._stream_crew_member(
                    target_crew_member,
                    message,
                    plan_id=None,
                    session_id=session_id,
                ):
                    pass
                return

            # No specific crew member mentioned - use producer if available
            producer_agent = self._get_producer_crew_member()
            if producer_agent:
                # producer_start event removed - no longer needed
                # await self._emit_system_event(
                #     "producer_start",
                #     session_id,
                #     crew_member_name=producer_agent.config.name,
                #     message=_extract_text_content(initial_prompt),
                # )
                async for _ in self._handle_producer_flow(
                    initial_prompt=initial_prompt,
                    producer_agent=producer_agent,
                    session_id=session_id,
                ):
                    pass
                return

            # No producer and no specific agent mentioned - select a responding agent
            responding_agent = await self._select_responding_agent(initial_prompt)
            if responding_agent:
                await self._emit_system_event(
                    "responding_agent_start",
                    session_id,
                    sender_id=responding_agent.config.name,
                    sender_name=responding_agent.config.name,
                    crew_member_name=responding_agent.config.name,
                    message=_extract_text_content(initial_prompt),
                )
                async for _ in self._stream_crew_member(
                    responding_agent,
                    _extract_text_content(initial_prompt),
                    plan_id=initial_prompt.metadata.get("plan_id") if initial_prompt.metadata else None,
                    session_id=session_id,
                    metadata=initial_prompt.metadata
                ):
                    pass
            else:
                async for _ in self._stream_error_message(
                    "No suitable agent found to handle this request.",
                    session_id,
                ):
                    pass
        except Exception as e:
            logger.error(f"❌ Exception in chat()", exc_info=True)
            async for _ in self._stream_error_message(
                f"An error occurred while processing your message: {str(e)}",
                str(uuid.uuid4()),
            ):
                pass

    async def _handle_producer_flow(
        self,
        initial_prompt: AgentMessage,
        producer_agent: CrewMember,
        session_id: str,
    ) -> AsyncGenerator["AgentEvent", None]:
        try:
            project_name = self._resolve_project_name()

            # Determine the active plan ID - get the last active plan for the project
            active_plan = self.plan_service.get_last_active_plan_for_project(project_name) if project_name else None
            active_plan_id = active_plan.id if active_plan else None

            # Generate message_id for producer's messages
            producer_message_id = str(uuid.uuid4())

            # Stream directly to the producer agent without creating a plan automatically
            # The producer will decide whether to create a plan using the production_plan skill
            async for event in self._stream_crew_member(
                producer_agent,
                _extract_text_content(initial_prompt),
                plan_id=active_plan_id,
                session_id=session_id,
                message_id=producer_message_id,
            ):
                try:
                    yield event
                except Exception as e:
                    logger.error(f"❌ Exception in _handle_producer_flow while yielding event", exc_info=True)

            # After the producer responds, check if a plan was created during the interaction
            # If a plan was created, execute the plan tasks
            if project_name:
                # Check if any plan was created during the producer's response
                # This would happen if the producer used the production_plan skill
                # Get the most recently created active plan for this project
                latest_plan = self.plan_service.get_last_active_plan_for_project(project_name)
                if latest_plan and latest_plan.id != active_plan_id:  # Only execute if a new plan was created
                    # Update the active plan ID to the newly created plan
                    active_plan_id = latest_plan.id

                    # Emit plan_update with producer as sender, using same message_id
                    await self._emit_system_event(
                        "plan_update",
                        session_id,
                        sender_id=producer_agent.config.name,
                        sender_name=producer_agent.config.name,
                        message_id=producer_message_id,
                        plan_id=latest_plan.id,
                    )

                    # Check if the plan has tasks to execute
                    if latest_plan and latest_plan.tasks:
                        async for event in self._execute_plan_tasks(
                            plan=latest_plan,
                            session_id=session_id,
                        ):
                            try:
                                yield event
                            except Exception as e:
                                logger.error(f"❌ Exception in _handle_producer_flow while yielding plan task event", exc_info=True)
        except Exception as e:
            logger.error(f"❌ Exception in _handle_producer_flow", exc_info=True)

    async def _execute_plan_tasks(
        self,
        plan: Plan,
        session_id: str,
    ) -> AsyncGenerator["AgentEvent", None]:
        try:
            plan_instance = self.plan_service.create_plan_instance(plan)
            self.plan_service.start_plan_execution(plan_instance)

            while True:
                ready_tasks = self._get_ready_tasks(plan_instance)
                if not ready_tasks:
                    if self._has_incomplete_tasks(plan_instance):
                        async for event in self._stream_error_message(
                            "Plan execution blocked by unmet dependencies or missing agents.",
                            session_id,
                        ):
                            try:
                                yield event
                            except Exception as e:
                                logger.error(f"❌ Exception in _execute_plan_tasks while yielding blocked event", exc_info=True)
                    break

                for task in ready_tasks:
                    self.plan_service.mark_task_running(plan_instance, task.id)
                    target_agent = self._crew_member_lookup.get(task.title.lower())
                    if not target_agent:
                        error_message = f"Crew member '{task.title}' not found for task {task.id}."
                        self.plan_service.mark_task_failed(plan_instance, task.id, error_message)
                        async for event in self._stream_error_message(
                            error_message,
                            session_id,
                        ):
                            try:
                                yield event
                            except Exception as e:
                                logger.error(f"❌ Exception in _execute_plan_tasks while yielding error event", exc_info=True)
                        continue

                    # Generate message_id for this task's crew member messages
                    task_message_id = str(uuid.uuid4())

                    # Emit plan_update with the crew member as sender, using same message_id
                    await self._emit_system_event(
                        "plan_update",
                        session_id,
                        sender_id=target_agent.config.name,
                        sender_name=target_agent.config.name,
                        message_id=task_message_id,
                        plan_id=plan.id,
                        task_id=task.id,
                        task_status="running",
                    )

                    task_message = self._build_task_message(task, plan.id)
                    async for event in self._stream_crew_member(
                        target_agent,
                        task_message,
                        plan_id=plan.id,
                        session_id=session_id,
                        metadata={"plan_id": plan.id, "task_id": task.id},
                        message_id=task_message_id,
                    ):
                        try:
                            yield event
                        except Exception as e:
                            logger.error(f"❌ Exception in _execute_plan_tasks while yielding task event", exc_info=True)

                    self.plan_service.mark_task_completed(plan_instance, task.id)
                    await self._emit_system_event(
                        "plan_update",
                        session_id,
                        sender_id=target_agent.config.name,
                        sender_name=target_agent.config.name,
                        message_id=task_message_id,
                        plan_id=plan.id,
                        task_id=task.id,
                        task_status="completed",
                    )

                updated_plan = self.plan_service.load_plan(plan.project_name, plan.id)
                if updated_plan:
                    plan_instance = self.plan_service.sync_plan_instance(plan_instance, updated_plan)
        except Exception as e:
            logger.error(f"❌ Exception in _execute_plan_tasks", exc_info=True)

    async def _select_responding_agent(self, message: AgentMessage) -> Optional[CrewMember]:
        """
        Select which agent should respond to a message based on content or routing rules.

        Args:
            message: The message to route

        Returns:
            CrewMember: The selected agent or None if no agent should respond
        """
        mentioned_agent = self._resolve_mentioned_title(_extract_text_content(message))
        if mentioned_agent:
            return mentioned_agent

        producer_agent = self.get_member(_PRODUCER_NAME)
        if producer_agent:
            return producer_agent

        content_lower = _extract_text_content(message).lower()
        for agent in self.members.values():
            if (hasattr(agent, 'config') and
                (agent.config.name.lower() in content_lower or
                 agent.config.name.lower().capitalize() in content_lower)):
                return agent

        if self.members:
            return next(iter(self.members.values()))

        return None

    def get_conversation_history(self) -> List[AgentMessage]:
        """Get the entire conversation history."""
        return self.conversation_history.copy()

    def clear_conversation_history(self):
        """Clear the conversation history."""
        self.conversation_history.clear()

    def connect_message_handler(self, receiver, weak: bool = True):
        """
        Connect a message handler to receive agent messages.

        This is a wrapper method for AgentChatSignals.connect().

        Args:
            receiver: A callable that will receive messages with signature (sender, **kwargs)
            weak: Whether to use a weak reference (default True)
        """
        self.signals.connect(receiver, weak=weak)

    def disconnect_message_handler(self, receiver):
        """
        Disconnect a message handler from receiving agent messages.

        This is a wrapper method for AgentChatSignals.disconnect().

        Args:
            receiver: The callable to disconnect
        """
        self.signals.disconnect(receiver)

    def update_context(self, project=None):
        """Update the agent context with new project information."""
        if project:
            self.project = project
            self._ensure_crew_members_loaded(refresh=True)

    async def broadcast_message(self, message: AgentMessage) -> AsyncIterator[AgentMessage]:
        """
        Broadcast a message to all agents and collect their responses.

        Args:
            message: The message to broadcast

        Yields:
            AgentMessage: Responses from all agents
        """
        from agent.react import AgentEventType

        for agent in self.members.values():
            try:
                # Extract text content from message structured_content
                message_text = ""
                if message.structured_content:
                    for sc in message.structured_content:
                        if sc.content_type.value == "text" and isinstance(sc.data, str):
                            message_text = sc.data
                            break

                # Iterate over ReactEvent from crew_member.chat_stream
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
                error_text = f"Error in agent {agent.config.name if hasattr(agent, 'config') else 'Unknown'}: {str(e)}"
                logger.error(f"❌ Exception in broadcast_to_all_agents", exc_info=True)
                error_msg = AgentMessage(
                    sender_id="system",
                    sender_name="System",
                    structured_content=[TextContent(text=error_text)]
                )
                logger.info(f"❌ Broadcasting error message: id={error_msg.message_id}, sender='system', content_preview='{error_text[:50]}{'...' if len(error_text) > 50 else ''}'")
                self.conversation_history.append(error_msg)
                yield error_msg