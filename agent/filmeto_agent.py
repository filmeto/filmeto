"""
Main agent module for Filmeto application.
Implements the FilmetoAgent class with streaming capabilities.
"""
import json
import logging
import re
import uuid
from typing import AsyncIterator, AsyncGenerator, Callable, Dict, List, Optional, Any, TYPE_CHECKING
from agent.chat.agent_chat_message import AgentMessage, StructureContent
from agent.chat.agent_chat_types import ContentType, MessageType
from agent.chat.agent_chat_signals import AgentChatSignals
from agent.llm.llm_service import LlmService
from agent.plan.models import Plan, PlanInstance, PlanTask, TaskStatus
from agent.plan.service import PlanService
from agent.crew.crew_member import CrewMember
from agent.crew.crew_title import sort_crew_members_by_title_importance
from agent.crew.crew_service import CrewService

if TYPE_CHECKING:
    from agent.event.agent_event import AgentEvent
    from agent.react.types import AgentEventType

logger = logging.getLogger(__name__)


_MENTION_PATTERN = re.compile(r"@([A-Za-z0-9_-]+)")
_PRODUCER_NAME = "producer"




class AgentStreamSession:
    """Represents a streaming session with the agent."""
    
    def __init__(self, session_id: str, initial_message: str):
        self.session_id = session_id
        self.initial_message = initial_message
        self.responses = []
        self.is_active = True


class StreamEvent:
    """Legacy: event payload for stream callbacks. Kept for tests; production uses AgentChatSignals."""

    def __init__(self, event_type: str, data: Any, timestamp: float = None):
        import time
        self.event_type = event_type
        self.data = data
        self.timestamp = timestamp or time.time()


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
        self.current_session: Optional[AgentStreamSession] = None
        self.llm_service = llm_service or LlmService(workspace)
        self.crew_member_service = crew_member_service or CrewService()
        self.plan_service = plan_service or PlanService()
        # Set the workspace if available to ensure proper plan storage location
        if self.workspace:
            self.plan_service.set_workspace(self.workspace)
        self.crew_members: Dict[str, CrewMember] = {}
        self._crew_member_lookup: Dict[str, CrewMember] = {}
        self.signals = AgentChatSignals()

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
        # Create lookup with both name and crew_title as keys
        self._crew_member_lookup = {}
        for name, agent in crew_members.items():
            # Add the agent by its name (current behavior)
            self._crew_member_lookup[name.lower()] = agent
            # Add the agent by its crew title (if available in metadata)
            crew_title = agent.config.metadata.get('crew_title')
            if crew_title:
                self._crew_member_lookup[crew_title.lower()] = agent

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
        for mention in self._extract_mentions(content):
            candidate = mention.lower()
            for agent in self.members.values():
                # Check against both the agent's name and any aliases in metadata
                if (hasattr(agent, 'config') and
                    (agent.config.name.lower() == candidate or
                     agent.config.name.lower().capitalize() == candidate)):
                    return agent
                # Also check for crew_title in metadata
                if (hasattr(agent, 'config') and
                    agent.config.metadata and
                    agent.config.metadata.get('crew_title', '').lower() == candidate):
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

    async def _emit_system_event(self, event_type: str, session_id: str, **kwargs: Any) -> None:
        """Emit a system event via AgentChatSignals for UI feedback."""
        meta = {"event_type": event_type, "session_id": session_id, **kwargs}
        msg = AgentMessage(
            message_type=MessageType.SYSTEM,
            sender_id="system",
            sender_name="System",
            metadata=meta,
            structured_content=[StructureContent(
                content_type=ContentType.METADATA,
                data={"event_type": event_type, **kwargs},
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
            if response.message_type == MessageType.TEXT:
                yield AgentEvent.final(
                    final_response=response.get_text_content(),
                    project_name=self._resolve_project_name() or "default",
                    react_type=response.sender_id,
                    run_id=getattr(self, "_run_id", ""),
                )
            elif response.message_type == MessageType.ERROR:
                yield AgentEvent.error(
                    error_message=response.get_text_content(),
                    project_name=self._resolve_project_name() or "default",
                    react_type=response.sender_id,
                    run_id=getattr(self, "_run_id", ""),
                )

    async def _stream_crew_member(
        self,
        crew_member: CrewMember,
        message: str,
        plan_id: Optional[str],
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator["AgentEvent", None]:
        from agent.react import AgentEvent, AgentEventType

        # Set the current message ID on the crew member for skill tracking
        crew_member._current_message_id = str(uuid.uuid4())

        async for event in crew_member.chat_stream(message, plan_id=plan_id):
            # Add metadata to the event
            event_payload = dict(event.payload)
            if metadata:
                event_payload.update(metadata)
            if plan_id:
                event_payload["plan_id"] = plan_id

            # Create a new event with enhanced metadata
            enhanced_event = AgentEvent.create(
                event_type=event.event_type,
                project_name=event.project_name,
                react_type=event.react_type,
                run_id=event.run_id,
                step_id=event.step_id,
                **event_payload
            )

            # Also send via AgentChatSignals for UI compatibility
            if event.event_type == AgentEventType.FINAL:
                final_text = event.payload.get("final_response", "")
                if final_text:
                    response = AgentMessage(
                        message_type=MessageType.TEXT,
                        sender_id=crew_member.config.name,
                        sender_name=crew_member.config.name.capitalize(),
                        metadata={"message_id": crew_member._current_message_id},
                        message_id=crew_member._current_message_id,
                        structured_content=[StructureContent(
                            content_type=ContentType.TEXT,
                            data=final_text
                        )]
                    )
                    logger.info(f"📤 Sending agent message: id={response.message_id}, sender='{response.sender_id}', content_preview='{final_text[:50]}{'...' if len(final_text) > 50 else ''}'")
                    await self.signals.send_agent_message(response)
            elif event.event_type == AgentEventType.ERROR:
                error_text = event.payload.get("error", "Unknown error")
                response = AgentMessage(
                    message_type=MessageType.ERROR,
                    sender_id=crew_member.config.name,
                    sender_name=crew_member.config.name.capitalize(),
                    metadata={"message_id": crew_member._current_message_id},
                    message_id=crew_member._current_message_id,
                    structured_content=[StructureContent(
                        content_type=ContentType.TEXT,
                        data=error_text
                    )]
                )
                logger.info(f"❌ Sending error message: id={response.message_id}, sender='{response.sender_id}', content_preview='{error_text[:50]}{'...' if len(error_text) > 50 else ''}'")
                await self.signals.send_agent_message(response)

            # Yield the event for upstream
            yield enhanced_event

    async def _stream_error_message(
        self,
        message: str,
        session_id: str,
    ) -> AsyncGenerator["AgentEvent", None]:
        from agent.react import AgentEvent, AgentEventType

        error_msg = AgentMessage(
            message_type=MessageType.ERROR,
            sender_id="system",
            sender_name="System",
            structured_content=[StructureContent(
                content_type=ContentType.TEXT,
                data=message
            )]
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
        )

    def get_current_session(self) -> Optional[AgentStreamSession]:
        """Get the current streaming session."""
        return self.current_session

    async def chat(self, message: str) -> None:
        """
        Send a message to the agents and receive responses via signals.

        This method does not return any value. Results are delivered through
        the AgentChatSignals system (send_agent_message signal).

        Args:
            message: The message to process
        """
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
        from agent.chat.agent_chat_message import StructureContent
        from agent.chat.agent_chat_types import ContentType
        initial_prompt = AgentMessage(
            message_type=MessageType.TEXT,
            sender_id="user",
            sender_name="User",
            structured_content=[StructureContent(
                content_type=ContentType.TEXT,
                data=message
            )]
        )
        logger.info(f"📥 Created initial prompt message: id={initial_prompt.message_id}, sender='user', content_preview='{message[:50]}{'...' if len(message) > 50 else ''}'")

        # Create a new session
        session_id = str(uuid.uuid4())
        self.current_session = AgentStreamSession(session_id, message)

        # Add the initial prompt to history
        self.conversation_history.append(initial_prompt)

        initial_prompt.metadata["session_id"] = session_id
        await self.signals.send_agent_message(initial_prompt)

        self._ensure_crew_members_loaded()

        mentioned_crew_member = self._resolve_mentioned_crew_member(message)
        if mentioned_crew_member and mentioned_crew_member.config.name.lower() != _PRODUCER_NAME:
            await self._emit_system_event(
                "crew_member_start",
                session_id,
                crew_member_name=mentioned_crew_member.config.name,
                message=message,
            )
            async for _ in self._stream_crew_member(
                mentioned_crew_member,
                message,
                plan_id=None,
                session_id=session_id,
            ):
                pass
            return

        producer_agent = self._get_producer_crew_member()
        if producer_agent:
            await self._emit_system_event(
                "producer_start",
                session_id,
                crew_member_name=producer_agent.config.name,
                message=initial_prompt.get_text_content(),
            )
            async for _ in self._handle_producer_flow(
                initial_prompt=initial_prompt,
                producer_agent=producer_agent,
                session_id=session_id,
            ):
                pass
            return

        mentioned_agent = self._resolve_mentioned_title(message)
        if mentioned_agent:
            await self._emit_system_event(
                "mentioned_agent_start",
                session_id,
                crew_member_name=mentioned_agent.config.name,
                message=initial_prompt.get_text_content(),
            )
            async for _ in self._stream_crew_member(
                mentioned_agent,
                initial_prompt.get_text_content(),
                plan_id=initial_prompt.metadata.get("plan_id") if initial_prompt.metadata else None,
                session_id=session_id,
                metadata=initial_prompt.metadata
            ):
                pass
            return

        # Prioritize producer if available and no specific agent is mentioned
        producer_agent = self._get_producer_crew_member()
        if producer_agent and not mentioned_crew_member:
            await self._emit_system_event(
                "producer_start",
                session_id,
                crew_member_name=producer_agent.config.name,
                message=initial_prompt.get_text_content(),
            )
            # Stream directly from the producer crew member
            async for _ in self._stream_crew_member(
                producer_agent,
                initial_prompt.get_text_content(),
                plan_id=initial_prompt.metadata.get("plan_id") if initial_prompt.metadata else None,
                session_id=session_id,
                metadata=initial_prompt.metadata
            ):
                pass
        else:
            responding_agent = await self._select_responding_agent(initial_prompt)
            if responding_agent:
                await self._emit_system_event(
                    "responding_agent_start",
                    session_id,
                    crew_member_name=responding_agent.config.name,
                    message=initial_prompt.get_text_content(),
                )
                async for _ in self._stream_crew_member(
                    responding_agent,
                    initial_prompt.get_text_content(),
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

    async def _handle_producer_flow(
        self,
        initial_prompt: AgentMessage,
        producer_agent: CrewMember,
        session_id: str,
    ) -> AsyncGenerator["AgentEvent", None]:
        project_name = self._resolve_project_name()

        # Determine the active plan ID - get the last active plan for the project
        active_plan = self.plan_service.get_last_active_plan_for_project(project_name) if project_name else None
        active_plan_id = active_plan.id if active_plan else None

        # Stream directly to the producer agent without creating a plan automatically
        # The producer will decide whether to create a plan using the create_execution_plan skill
        async for event in self._stream_crew_member(
            producer_agent,
            initial_prompt.get_text_content(),
            plan_id=active_plan_id,
            session_id=session_id,
        ):
            yield event

        # After the producer responds, check if a plan was created during the interaction
        # If a plan was created, execute the plan tasks
        if project_name:
            # Check if any plan was created during the producer's response
            # This would happen if the producer used the create_execution_plan skill
            # Get the most recently created active plan for this project
            latest_plan = self.plan_service.get_last_active_plan_for_project(project_name)
            if latest_plan and latest_plan.id != active_plan_id:  # Only execute if a new plan was created
                # Update the active plan ID to the newly created plan
                active_plan_id = latest_plan.id

                await self._emit_system_event(
                    "plan_update",
                    session_id,
                    plan_id=latest_plan.id,
                )

                # Check if the plan has tasks to execute
                if latest_plan and latest_plan.tasks:
                    async for event in self._execute_plan_tasks(
                        plan=latest_plan,
                        session_id=session_id,
                    ):
                        yield event

    async def _execute_plan_tasks(
        self,
        plan: Plan,
        session_id: str,
    ) -> AsyncGenerator["AgentEvent", None]:
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
                        yield event
                break

            for task in ready_tasks:
                self.plan_service.mark_task_running(plan_instance, task.id)
                await self._emit_system_event(
                    "plan_update",
                    session_id,
                    plan_id=plan.id,
                    task_id=task.id,
                    task_status="running",
                )
                target_agent = self._crew_member_lookup.get(task.title.lower())
                if not target_agent:
                    error_message = f"Crew member '{task.title}' not found for task {task.id}."
                    self.plan_service.mark_task_failed(plan_instance, task.id, error_message)
                    async for event in self._stream_error_message(
                        error_message,
                        session_id,
                    ):
                        yield event
                    continue

                task_message = self._build_task_message(task, plan.id)
                async for event in self._stream_crew_member(
                    target_agent,
                    task_message,
                    plan_id=plan.id,
                    session_id=session_id,
                    metadata={"plan_id": plan.id, "task_id": task.id},
                ):
                    yield event

                self.plan_service.mark_task_completed(plan_instance, task.id)
                await self._emit_system_event(
                    "plan_update",
                    session_id,
                    plan_id=plan.id,
                    task_id=task.id,
                    task_status="completed",
                )

            updated_plan = self.plan_service.load_plan(plan.project_name, plan.id)
            if updated_plan:
                plan_instance = self.plan_service.sync_plan_instance(plan_instance, updated_plan)

    async def _select_responding_agent(self, message: AgentMessage) -> Optional[CrewMember]:
        """
        Select which agent should respond to a message based on content or routing rules.

        Args:
            message: The message to route

        Returns:
            CrewMember: The selected agent or None if no agent should respond
        """
        mentioned_agent = self._resolve_mentioned_title(message.get_text_content())
        if mentioned_agent:
            return mentioned_agent

        producer_agent = self.get_member(_PRODUCER_NAME)
        if producer_agent:
            return producer_agent

        content_lower = message.get_text_content().lower()
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
                                message_type=MessageType.TEXT,
                                sender_id=agent.config.name,
                                sender_name=agent.config.name.capitalize(),
                                metadata={},
                                structured_content=[StructureContent(
                                    content_type=ContentType.TEXT,
                                    data=final_text
                                )]
                            )
                            self.conversation_history.append(response)
                            yield response
                    elif event.event_type == AgentEventType.ERROR:
                        error_text = event.payload.get("error", "Unknown error")
                        error_msg = AgentMessage(
                            message_type=MessageType.ERROR,
                            sender_id=agent.config.name,
                            sender_name=agent.config.name.capitalize(),
                            metadata={},
                            structured_content=[StructureContent(
                                content_type=ContentType.TEXT,
                                data=error_text
                            )]
                        )
                        self.conversation_history.append(error_msg)
                        yield error_msg
            except Exception as e:
                error_text = f"Error in agent {agent.config.name if hasattr(agent, 'config') else 'Unknown'}: {str(e)}"
                error_msg = AgentMessage(
                    message_type=MessageType.ERROR,
                    sender_id="system",
                    sender_name="System",
                    structured_content=[StructureContent(
                        content_type=ContentType.TEXT,
                        data=error_text
                    )]
                )
                logger.info(f"❌ Broadcasting error message: id={error_msg.message_id}, sender='system', content_preview='{error_text[:50]}{'...' if len(error_text) > 50 else ''}'")
                self.conversation_history.append(error_msg)
                yield error_msg