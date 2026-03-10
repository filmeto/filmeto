import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, TYPE_CHECKING

import yaml

from agent.chat.agent_chat_message import AgentMessage, StructureContent
from agent.chat.agent_chat_signals import AgentChatSignals
from agent.chat.agent_chat_types import ContentType
from agent.llm.llm_service import LlmService
from agent.plan.plan_service import PlanService
from agent.skill.skill_service import SkillService, Skill
from agent.soul import soul_service as soul_service_instance, SoulService
from agent.prompt.prompt_service import prompt_service
from agent.crew.crew_member_history_service import crew_member_history_service

if TYPE_CHECKING:
    from agent.event.agent_event import AgentEvent
    from agent.react.types import AgentEventType

logger = logging.getLogger(__name__)


@dataclass
class CrewMemberConfig:
    name: str
    description: str = ""
    soul: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    prompt: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.4
    max_steps: int = 5
    color: str = "#4a90e2"  # Default color for the agent's icon
    icon: str = "🤖"  # Default icon for the agent
    metadata: Dict[str, Any] = field(default_factory=dict)
    config_path: Optional[str] = None

    @classmethod
    def from_markdown(cls, file_path: str) -> "CrewMemberConfig":
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        metadata, prompt = _parse_frontmatter(content)
        name = metadata.get("name") or os.path.splitext(os.path.basename(file_path))[0]
        description = metadata.get("description", "")
        soul = metadata.get("soul")
        skills = _normalize_list(metadata.get("skills", []))
        model = metadata.get("model", "gpt-4o-mini")
        temperature = float(metadata.get("temperature", 0.4))
        max_steps = int(metadata.get("max_steps", 5))
        color = metadata.get("color", "#4a90e2")  # Get color from metadata, default to blue
        icon = metadata.get("icon", "🤖")  # Get icon from metadata, default to robot

        return cls(
            name=name,
            description=description,
            soul=soul,
            skills=skills,
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_steps=max_steps,
            color=color,
            icon=icon,
            metadata=metadata,
            config_path=file_path,
        )


class CrewMember:
    """
    A ReAct-style crew member driven by LLM and skill execution.
    """

    def __init__(
        self,
        config_path: str,
        workspace: Any = None,
        project: Any = None,
        llm_service: Optional[LlmService] = None,
        skill_service: Optional[SkillService] = None,
        soul_service: Optional[SoulService] = None,
        plan_service: Optional[PlanService] = None,
    ):
        self.config = CrewMemberConfig.from_markdown(config_path)
        self.workspace = workspace
        self.project = project
        self.project_name = _resolve_project_name(project) or getattr(project, 'project_name', 'default_project')
        # Get crew_title from metadata or derive from name
        self.crew_title = self.config.metadata.get('crew_title', self.config.name.lower().replace(' ', '_'))
        self.llm_service = llm_service or LlmService(workspace)
        self.skill_service = skill_service or SkillService(workspace)
        # Get PlanService instance for this workspace/project combination
        self.plan_service = plan_service or PlanService.get_instance(workspace, self.project_name)
        self.soul_service = soul_service or self._build_soul_service(project)
        self.conversation_history: List[Dict[str, str]] = []

    async def chat_stream(
        self,
        message: str,
        plan_id: Optional[str] = None,
        sender_id: str = "user",
        sender_name: str = "User",
    ) -> AsyncIterator["AgentEvent"]:
        """
        Stream chat responses as ReactEvent objects.

        Args:
            message: The user message to process
            plan_id: Optional plan ID for context
            sender_id: ID of the message sender. Use "user" for direct private chat,
                      "system" or other values for group chat routing.
            sender_name: Display name of the sender.

        Yields:
            ReactEvent: Events from the ReAct execution process
        """
        from agent.react import react_service, AgentEventType, AgentEvent
        from agent.chat.content import TypingContent, TypingState

        # Generate a run_id for this session
        import uuid
        run_id = str(uuid.uuid4())
        # Generate a single message_id for all events in this conversation turn
        # This ensures all events (LLM_THINKING, TOOL_*, FINAL, etc.) share the same message_id
        message_id = str(uuid.uuid4())

        # First, save the user message to history BEFORE any crew member events
        # This ensures correct ordering: user message -> crew member events
        self._save_message_to_history("user", message, run_id, sender_id=sender_id, sender_name=sender_name)

        # Then, emit a typing event to give immediate visual feedback
        typing_start_event = AgentEvent.create(
            event_type=AgentEventType.CREW_MEMBER_TYPING.value,
            project_name=self.project_name,
            react_type=self.config.name,
            run_id=run_id,
            step_id=0,
            sender_id=self.config.name,
            sender_name=self.config.name,
            content=TypingContent(
                title="Typing",
                description="Agent is processing your request",
                state=TypingState.START
            )
        )
        # Save typing start event to history
        self._save_event_to_history(typing_start_event, message_id)
        yield typing_start_event

        if not self.llm_service.validate_config():
            # Yield error event first
            error_event = AgentEvent.error(
                error_message="LLM service is not configured.",
                project_name=self.project_name,
                react_type=self.config.name,
                run_id=run_id,
                step_id=0,
                sender_id=self.config.name,
                sender_name=self.config.name,
            )
            # Save error event to history
            self._save_event_to_history(error_event, message_id)
            yield error_event
            # Emit typing_end event after error to mark completion
            typing_end_event = AgentEvent.create(
                event_type=AgentEventType.CREW_MEMBER_TYPING_END.value,
                project_name=self.project_name,
                react_type=self.config.name,
                run_id=run_id,
                step_id=0,
                sender_id=self.config.name,
                sender_name=self.config.name,
                content=TypingContent(
                    title="Typing",
                    description="Agent processing completed",
                    state=TypingState.END
                )
            )
            # Save typing end event to history
            self._save_event_to_history(typing_end_event, message_id)
            yield typing_end_event
            return

        def build_prompt_function(user_question: str) -> str:
            return self._build_user_prompt(user_question, plan_id=plan_id)

        # Build available tool names - use execute_skill and todo as tools
        available_tool_names = ["execute_skill", "todo"]

        react_instance = react_service.get_or_create_react(
            project_name=self.project_name,
            react_type=self.config.name,
            build_prompt_function=build_prompt_function,
            available_tool_names=available_tool_names,
            workspace=self.workspace,
            llm_service=self.llm_service,
            max_steps=self.config.max_steps,
        )

        final_response = None
        saw_event = False

        async for event in react_instance.chat_stream(message):
            saw_event = True

            # Enhance event with sender information and preserve content
            enhanced_event = AgentEvent.create(
                event_type=event.event_type,
                project_name=event.project_name,
                react_type=event.react_type,
                run_id=event.run_id,
                step_id=event.step_id,
                sender_id=self.config.name,
                sender_name=self.config.name,
                content=event.content  # Preserve the original content
            )

            # Save ALL events to crew member history for complete traceability
            # Use the same message_id for all events in this conversation turn
            self._save_event_to_history(enhanced_event, message_id)

            if event.event_type == AgentEventType.FINAL:
                # Extract from content or payload (backward compat)
                if event.content and hasattr(event.content, 'text'):
                    final_response = event.content.text
                elif event.payload:
                    final_response = event.payload.get("final_response", "")
                else:
                    final_response = ""
                # Store conversation history
                if final_response:
                    self.conversation_history.append({"role": "user", "content": message})
                    self.conversation_history.append({"role": "assistant", "content": final_response})
                    # Save assistant response to history storage
                    self._save_message_to_history("assistant", final_response, run_id)
                # Yield final response first
                yield enhanced_event
                # Emit typing_end event after final response to mark completion
                typing_end_event = AgentEvent.create(
                    event_type=AgentEventType.CREW_MEMBER_TYPING_END.value,
                    project_name=self.project_name,
                    react_type=self.config.name,
                    run_id=event.run_id,
                    step_id=event.step_id,
                    sender_id=self.config.name,
                    sender_name=self.config.name,
                    content=TypingContent(
                        title="Typing",
                        description="Agent processing completed",
                        state=TypingState.END
                    )
                )
                # Save typing end event to history
                self._save_event_to_history(typing_end_event, message_id)
                yield typing_end_event
                break
            elif event.event_type == AgentEventType.ERROR:
                # Extract from content or payload (backward compat)
                if event.content and hasattr(event.content, 'error_message'):
                    error_message = event.content.error_message
                elif event.payload:
                    error_message = event.payload.get("error", "Unknown error occurred")
                else:
                    error_message = "Unknown error occurred"
                self.conversation_history.append({"role": "user", "content": message})
                self.conversation_history.append({"role": "assistant", "content": error_message})
                # Save assistant error to history storage
                self._save_message_to_history("assistant", error_message, run_id, is_error=True)
                # Yield error event first
                yield enhanced_event
                # Emit typing_end event after error to mark completion
                typing_end_event = AgentEvent.create(
                    event_type=AgentEventType.CREW_MEMBER_TYPING_END.value,
                    project_name=self.project_name,
                    react_type=self.config.name,
                    run_id=event.run_id,
                    step_id=event.step_id,
                    sender_id=self.config.name,
                    sender_name=self.config.name,
                    content=TypingContent(
                        title="Typing",
                        description="Agent processing completed",
                        state=TypingState.END
                    )
                )
                # Save typing end event to history
                self._save_event_to_history(typing_end_event, message_id)
                yield typing_end_event
                break
            else:
                # Yield all other events (LLM_THINKING, TOOL_START, TOOL_PROGRESS, TOOL_END, etc.)
                yield enhanced_event

        if not saw_event:
            return

        if final_response is None:
            error_msg = "Reached max steps without a final response."
            # Save assistant error to history storage
            self._save_message_to_history("assistant", error_msg, run_id, is_error=True)
            # Yield error event first
            error_event = AgentEvent.error(
                error_message=error_msg,
                project_name=self.project_name,
                react_type=self.config.name,
                run_id=run_id,
                sender_id=self.config.name,
                sender_name=self.config.name,
            )
            # Save error event to history
            self._save_event_to_history(error_event, message_id)
            yield error_event
            # Emit typing_end event after error to mark completion
            typing_end_event = AgentEvent.create(
                event_type=AgentEventType.CREW_MEMBER_TYPING_END.value,
                project_name=self.project_name,
                react_type=self.config.name,
                run_id=run_id,
                step_id=0,
                sender_id=self.config.name,
                sender_name=self.config.name,
                content=TypingContent(
                    title="Typing",
                    description="Agent processing completed",
                    state=TypingState.END
                )
            )
            # Save typing end event to history
            self._save_event_to_history(typing_end_event, message_id)
            yield typing_end_event
            return

    def _save_message_to_history(
        self,
        role: str,
        content: str,
        run_id: str,
        is_error: bool = False,
        sender_id: Optional[str] = None,
        sender_name: Optional[str] = None,
    ):
        """
        Save a message to the crew member's history storage.

        Args:
            role: Message role ("user" or "assistant")
            content: Message content
            run_id: Run ID for this conversation session
            is_error: Whether this is an error message
            sender_id: Sender ID (defaults to role-based: crew member name for assistant, "user" for user)
            sender_name: Sender display name (defaults to sender_id)
        """
        if not self.workspace or not self.project_name:
            return

        try:
            workspace_path = _get_workspace_path(self.workspace)

            # Determine sender based on role if not provided
            if role == "assistant":
                final_sender_id = sender_id or self.config.name
                final_sender_name = sender_name or self.config.name
            else:
                final_sender_id = sender_id or "user"
                final_sender_name = sender_name or "User"

            message_dict = {
                "message_id": str(uuid.uuid4()),
                "run_id": run_id,
                "role": role,
                "sender_id": final_sender_id,
                "sender_name": final_sender_name,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "crew_title": self.crew_title,
                "is_error": is_error,
            }

            crew_member_history_service.add_message(
                workspace_path=workspace_path,
                project_name=self.project_name,
                crew_title=self.crew_title,
                message=message_dict
            )
        except Exception as e:
            logger.error(f"Error saving message to history: {e}")

    def _save_event_to_history(self, event: "AgentEvent", message_id: Optional[str] = None):
        """
        Save an AgentEvent to the crew member's history storage.

        This method serializes the entire AgentEvent including its content,
        allowing crew member history to capture full execution details like
        LLM thinking, tool calls, skill execution, etc.

        Args:
            event: The AgentEvent to save
            message_id: Optional message ID to use. If not provided, generates a new one.
                       For events in the same conversation turn, pass the same message_id
                       to group them together in the UI.
        """
        if not self.workspace or not self.project_name:
            return

        try:
            workspace_path = _get_workspace_path(self.workspace)

            # Serialize event content to dictionary
            content_dict = {}
            if event.content:
                content_dict = event.content.to_dict()

            # Use provided message_id or generate a new one
            # IMPORTANT: For streaming responses, all events should share the same message_id
            event_message_id = message_id if message_id else str(uuid.uuid4())

            # Build event message dictionary with full event details
            event_dict = {
                "message_id": event_message_id,
                "run_id": event.run_id,
                "role": "event",  # Special role to identify event messages
                "sender_id": event.sender_id or self.config.name,
                "sender_name": event.sender_name or self.config.name,
                "event_type": event.event_type,
                "step_id": event.step_id,
                "timestamp": datetime.now().isoformat(),
                "crew_title": self.crew_title,
                "content": content_dict,
                "is_event": True,  # Flag to identify event messages
            }

            crew_member_history_service.add_message(
                workspace_path=workspace_path,
                project_name=self.project_name,
                crew_title=self.crew_title,
                message=event_dict
            )
            logger.debug(f"Saved event {event.event_type} to crew member {self.crew_title} history")
        except Exception as e:
            logger.error(f"Error saving event to history: {e}")

    def get_history_latest(self, count: int = 20) -> List[Dict[str, Any]]:
        """
        Get the latest N messages from this crew member's history.

        Args:
            count: Number of messages to retrieve

        Returns:
            List of message dictionaries, most recent first
        """
        if not self.workspace or not self.project_name:
            return []

        try:
            workspace_path = _get_workspace_path(self.workspace)

            return crew_member_history_service.get_latest_messages(
                workspace_path=workspace_path,
                project_name=self.project_name,
                crew_title=self.crew_title,
                count=count
            )
        except Exception as e:
            logger.error(f"Error getting latest history: {e}")
            return []

    def get_history_after(self, line_offset: int, count: int = 20) -> List[Dict[str, Any]]:
        """
        Get messages after a given line offset.

        Args:
            line_offset: Line offset in active log
            count: Number of messages to retrieve

        Returns:
            List of message dictionaries in chronological order
        """
        if not self.workspace or not self.project_name:
            return []

        try:
            workspace_path = _get_workspace_path(self.workspace)

            return crew_member_history_service.get_messages_after(
                workspace_path=workspace_path,
                project_name=self.project_name,
                crew_title=self.crew_title,
                line_offset=line_offset,
                count=count
            )
        except Exception as e:
            logger.error(f"Error getting history after offset: {e}")
            return []

    def get_history_before(self, line_offset: int, count: int = 20) -> List[Dict[str, Any]]:
        """
        Get messages before a given line offset.

        Args:
            line_offset: Starting line offset (exclusive)
            count: Number of messages to retrieve

        Returns:
            List of message dictionaries in chronological order
        """
        if not self.workspace or not self.project_name:
            return []

        try:
            workspace_path = _get_workspace_path(self.workspace)

            return crew_member_history_service.get_messages_before(
                workspace_path=workspace_path,
                project_name=self.project_name,
                crew_title=self.crew_title,
                line_offset=line_offset,
                count=count
            )
        except Exception as e:
            logger.error(f"Error getting history before offset: {e}")
            return []

    def get_history_count(self) -> int:
        """
        Get total message count for this crew member's history.

        Returns:
            Total number of messages
        """
        if not self.workspace or not self.project_name:
            return 0

        try:
            workspace_path = _get_workspace_path(self.workspace)

            return crew_member_history_service.get_total_count(
                workspace_path=workspace_path,
                project_name=self.project_name,
                crew_title=self.crew_title
            )
        except Exception as e:
            logger.error(f"Error getting history count: {e}")
            return 0

    def clear_history(self) -> bool:
        """
        Clear all history for this crew member.

        Returns:
            True if successful
        """
        if not self.workspace or not self.project_name:
            return False

        try:
            workspace_path = _get_workspace_path(self.workspace)

            return crew_member_history_service.clear_history(
                workspace_path=workspace_path,
                project_name=self.project_name,
                crew_title=self.crew_title
            )
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            return False

    def _build_user_prompt(self, user_question: str, plan_id: Optional[str] = None) -> str:
        """Build a user prompt that embeds the user's question into the react_base template.

        Args:
            user_question: The user's question(s). May contain multiple questions separated by newlines.
            plan_id: Optional plan ID for context.
        """
        soul_content = self._get_formatted_soul_prompt()

        # Prepare skills as structured data for the template
        skills_list = self._get_skills_as_structured_list()

        # Get crew members info for team context
        crew_members_info = self._get_crew_members_info()

        # Build context info
        context_info_parts = []
        if plan_id:
            context_info_parts.append(f"Active plan id: {plan_id}.")
        elif self.project_name:
            context_info_parts.append(f"Project name: {self.project_name}.")

        # Add the user's question to the context
        # Use newline separator for context parts to properly format multi-line questions
        user_question_prefix = "User's questions:" if "\n" in user_question else "User's question:"
        context_info_parts.append(f"{user_question_prefix} {user_question}")

        # Join with newlines to preserve multi-line formatting
        context_info = "\n".join(context_info_parts)

        user_prompt = prompt_service.render_prompt(
            name="crew_member_react",
            title="crew member",
            agent_name=self.config.name,
            role_description=f"Role description: {self.config.description}" if self.config.description else "",
            soul_profile=soul_content,
            skills_list=skills_list,
            context_info=context_info,
            crew_members_info=crew_members_info,
        )

        # If the base prompt template is not available, fall back to the original method
        if user_prompt is None:
            prompt_sections = [
                "You are a ReAct-style crew member.",
                f"Crew member name: {self.config.name}.",
            ]
            if self.config.description:
                prompt_sections.append(f"Role description: {self.config.description}")

            # soul_content already includes soul + crew_title + custom_prompt from get_full_knowledge()
            if soul_content.strip():
                prompt_sections.append("Soul profile:")
                prompt_sections.append(soul_content)

            skills_prompt = self._format_skills_prompt()
            prompt_sections.append(skills_prompt)

            # Include context info with user question
            prompt_sections.append(context_info)

            user_prompt = "\n\n".join(section for section in prompt_sections if section)

        return user_prompt

    def _build_soul_service(self, project: Optional[Any]) -> 'SoulService':
        # Return the singleton instance
        # The singleton is configured elsewhere with the workspace
        return soul_service_instance

    def _build_system_prompt(self, plan_id: Optional[str] = None) -> str:
        # Use the prompt service to get the base ReAct template
        soul_content = self._get_formatted_soul_prompt()

        # Prepare skills as structured data for the template
        skills_list = self._get_skills_as_structured_list()

        # Get crew members info for team context
        crew_members_info = self._get_crew_members_info()

        base_prompt = prompt_service.render_prompt(
            name="crew_member_react",
            title="crew member",
            agent_name=self.config.name,
            role_description=f"Role description: {self.config.description}" if self.config.description else "",
            soul_profile=soul_content,
            skills_list=skills_list,
            context_info=f"Active plan id: {plan_id}." if plan_id else f"Project name: {self.project_name}." if self.project_name else "",
            crew_members_info=crew_members_info,
        )

        # If the base prompt template is not available, fall back to the original method
        if base_prompt is None:
            prompt_sections = [
                "You are a ReAct-style crew member.",
                f"Crew member name: {self.config.name}.",
            ]
            if self.config.description:
                prompt_sections.append(f"Role description: {self.config.description}")

            # soul_content already includes soul + crew_title + custom_prompt from get_full_knowledge()
            if soul_content.strip():
                prompt_sections.append("Soul profile:")
                prompt_sections.append(soul_content)

            skills_prompt = self._format_skills_prompt()
            prompt_sections.append(skills_prompt)

            if plan_id:
                prompt_sections.append(f"Active plan id: {plan_id}.")
            elif self.project_name:
                prompt_sections.append(f"Project name: {self.project_name}.")

            return "\n\n".join(section for section in prompt_sections if section)

        return base_prompt

    def _get_skills_as_structured_list(self) -> list:
        """Get skills as a structured list for advanced templating."""
        language = self._get_language()
        if not self.config.skills:
            # If no skills are configured for this crew member, fall back to all available skills
            return self._get_all_available_skills_as_structured_list(language)

        skills_list = []
        for name in self.config.skills:
            skill = self.skill_service.get_skill(name, language=language)
            if not skill:
                continue  # Skip unavailable skills

            # Extract triggers from skill knowledge for better instruction following
            triggers = self._extract_skill_triggers(skill.knowledge)

            skills_list.append({
                'name': skill.name,
                'description': skill.description,
                'triggers': triggers,
            })

        return skills_list

    def _extract_skill_triggers(self, knowledge: str, max_length: int = 500) -> str:
        """Extract trigger conditions from skill knowledge.

        Looks for 'When to Use' sections and extracts relevant trigger keywords.

        Args:
            knowledge: The skill knowledge string
            max_length: Maximum length for the extracted triggers

        Returns:
            Extracted trigger conditions or empty string
        """
        if not knowledge:
            return ""

        # Try to find "When to Use" section
        import re

        # Common patterns for trigger sections
        patterns = [
            r'##\s*When to Use[^#]*',
            r'##\s*何时使用[^#]*',
            r'##\s*使用场景[^#]*',
            r'\*\*When to Use[^*]*\*\*[^#]*',
        ]

        for pattern in patterns:
            match = re.search(pattern, knowledge, re.IGNORECASE | re.DOTALL)
            if match:
                triggers = match.group(0).strip()
                if len(triggers) > max_length:
                    triggers = triggers[:max_length] + "..."
                return triggers

        # Fallback: return first part of knowledge if no specific section found
        if len(knowledge) > max_length:
            return knowledge[:max_length] + "..."
        return knowledge

    def _get_all_available_skills_as_structured_list(self, language: str = None) -> list:
        """Get all available skills as a structured list for advanced templating."""
        all_skills = self.skill_service.get_all_skills(language=language)

        skills_list = []
        for skill in all_skills:  # all_skills is a list, not a dict
            # Extract triggers from skill knowledge
            triggers = self._extract_skill_triggers(skill.knowledge)

            skills_list.append({
                'name': skill.name,
                'description': skill.description,
                'triggers': triggers,
            })

        return skills_list

    def get_full_knowledge(self) -> str:
        """
        Get the full knowledge for this crew member by combining:
        1. Soul knowledge (if soul is configured)
        2. Crew title role description
        3. User custom knowledge (from prompt field)

        Returns:
            Combined knowledge string with all three components
        """
        parts = []

        # 1. Get soul knowledge
        soul_knowledge = self._get_soul_knowledge()
        if soul_knowledge:
            parts.append(soul_knowledge)

        # 2. Get crew title role description
        crew_title_info = self._get_crew_title_info()
        if crew_title_info:
            parts.append(crew_title_info)

        # 3. Get user custom knowledge (from prompt field)
        custom_knowledge = self.config.prompt or ""
        if custom_knowledge:
            parts.append(custom_knowledge)

        # Combine all parts
        if not parts:
            return ""

        # If there's only one part, return it directly
        if len(parts) == 1:
            return parts[0]

        # Join with clear section separators
        return "\n\n---\n\n".join(parts)

    def _get_soul_knowledge(self) -> str:
        """Get soul knowledge for this crew member."""
        if not self.config.soul:
            return ""
        soul = self.soul_service.get_soul_by_name(self.project_name, self.config.soul)
        if not soul:
            return ""
        if soul.knowledge:
            return soul.knowledge
        return ""

    def _get_crew_title_info(self) -> str:
        """Get crew title role description and content."""
        from .crew_title import CrewTitle
        from utils.md_with_meta_utils import get_content

        crew_title = self.config.metadata.get('crew_title', '') if hasattr(self.config, 'metadata') and self.config.metadata else ''
        if not crew_title:
            return ""

        parts = []

        # Get crew title metadata
        crew_title_metadata = CrewTitle.get_crew_title_metadata(crew_title)
        description = crew_title_metadata.get('description', '')
        if description:
            parts.append(f"Role: {description}")

        # Get crew title content (the "You are the..." part from the .md file)
        try:
            current_language = self._get_language()
            # Get the correct path to crew system directory
            system_base_dir = Path(os.path.dirname(__file__)) / "system"

            # Determine language-specific directory
            if current_language == "zh_CN":
                system_dir = system_base_dir / "zh_CN"
            elif current_language == "en_US":
                system_dir = system_base_dir / "en_US"
            else:
                system_dir = system_base_dir / "en_US"

            # Fallback to base directory if language-specific directory doesn't exist
            if not system_dir.exists():
                system_dir = system_base_dir

            # Get the crew title .md file path
            md_file_path = system_dir / f"{crew_title}.md"
            if md_file_path.exists():
                content = get_content(md_file_path)
                if content and content.strip():
                    parts.append(content.strip())
        except Exception as e:
            logger.debug(f"Could not read crew title content for {crew_title}: {e}")

        # Combine into a single string
        return "\n\n".join(parts) if parts else ""

    def _get_formatted_soul_prompt(self) -> str:
        """Get formatted full knowledge prompt for use in system prompt."""
        return self.get_full_knowledge()

    def _get_crew_members_info(self) -> str:
        """Get formatted information about all crew members in the project.

        Returns:
            A formatted string containing information about all crew members,
            including their names, roles, descriptions, and skills.
        """
        from .crew_service import CrewService

        try:
            crew_service = CrewService()
            crew_members_dict = crew_service.get_project_crew_members(self.project)

            if not crew_members_dict:
                return ""

            # Sort crew members by title importance
            from .crew_title import sort_crew_members_by_title_importance
            sorted_members = sort_crew_members_by_title_importance(crew_members_dict)

            member_info_list = []
            for member in sorted_members:
                # Skip the current member in the list to avoid redundancy
                if member.config.name == self.config.name:
                    continue

                # Format each member's information
                # crew_title is stored in metadata
                role = member.config.metadata.get('crew_title', member.config.name) if member.config.metadata else member.config.name
                skills_str = ", ".join(member.config.skills) if member.config.skills else "None"
                description = member.config.description or "No description available"

                member_info = f"- **{member.config.name}** (role: {role})\n  - Description: {description}\n  - Skills: {skills_str}"
                member_info_list.append(member_info)

            if not member_info_list:
                return ""

            return "\n\n".join(member_info_list)

        except Exception as e:
            logger.debug(f"Could not get crew members info: {e}")
            return ""

    def _format_skills_prompt(self) -> str:
        language = self._get_language()
        if not self.config.skills:
            # If no skills are configured for this crew member, fall back to all available skills
            return self._get_all_available_skills_prompt(language)

        details = []
        missing = []
        for name in self.config.skills:
            skill = self.skill_service.get_skill(name, language=language)
            if not skill:
                missing.append(name)
                continue
            details.append(_format_skill_entry_detailed(skill))

        if not details:
            # If none of the configured skills are available, fall back to all available skills
            return self._get_all_available_skills_prompt(language)
        else:
            skills_section = (
                "## Available Skills\n\n"
                "You have access to the following skills. Review each skill's purpose to decide when to use it.\n\n"
                + "\n\n".join(details)
            )

        if missing:
            skills_section += f"\n\nNote: The following skills are configured but not available: {', '.join(missing)}"

        return skills_section

    def _get_all_available_skills_prompt(self, language: str = None) -> str:
        """Get a prompt with all available skills in the project as a fallback."""
        all_skills = self.skill_service.get_all_skills(language=language)

        if not all_skills:
            return "Available skills: none.\nYou cannot call any skills."

        details = []
        for skill in all_skills:  # all_skills is a list, not a dict
            details.append(_format_skill_entry_detailed(skill))

        if not details:
            return "Available skills: none.\nYou cannot call any skills."

        return (
            "## Available Skills\n\n"
            "You have access to the following skills. Review each skill's purpose to decide when to use it.\n\n"
            + "\n\n".join(details)
        )

    def _get_language(self) -> str:
        """Get the language setting for the crew member."""
        # Try to get language from project
        if self.project and hasattr(self.project, 'get_language'):
            return self.project.get_language()

        # Fallback: try to get language from workspace settings
        if self.workspace and hasattr(self.workspace, 'settings'):
            try:
                language = self.workspace.settings.get("general.language", "en")
                # Convert language code to our format (en -> en_US, zh -> zh_CN)
                if language == "zh_CN" or language == "zh":
                    return "zh_CN"
                else:
                    return "en_US"
            except:
                pass

        # Default to en_US
        return "en_US"



def _parse_frontmatter(content: str) -> (Dict[str, Any], str):
    if content.startswith("---"):
        end_idx = content.find("---", 3)
        if end_idx != -1:
            meta_str = content[3:end_idx].strip()
            try:
                metadata = yaml.safe_load(meta_str) or {}
            except Exception:
                metadata = {}
            prompt = content[end_idx + 3 :].strip()
            return metadata, prompt
    return {}, content.strip()


def _normalize_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        if "," in value:
            return [item.strip() for item in value.split(",") if item.strip()]
        return [value.strip()] if value.strip() else []
    return [str(value).strip()]


def _format_skill_entry(skill: Skill) -> str:
    """Legacy simple skill formatting."""
    description = skill.description or ""
    knowledge = skill.knowledge or ""
    return f"- {skill.name}: {description}\n  {knowledge}"


def _format_skill_entry_detailed(skill: Skill) -> str:
    """Format a skill entry with metadata to help the LLM decide whether to use the skill."""
    lines = [
        f"### {skill.name}",
        f"**Description**: {skill.description}",
        "",
    ]

    return "\n".join(lines)


def _resolve_project_name(project: Optional[Any]) -> Optional[str]:
    if project is None:
        return None
    if hasattr(project, "project_name"):
        return project.project_name
    if hasattr(project, "name"):
        return project.name
    if isinstance(project, str):
        return project
    return None


def _get_workspace_path(workspace: Any) -> str:
    """Extract workspace path from workspace object."""
    if workspace is None:
        return "none"
    if hasattr(workspace, 'workspace_path'):
        return workspace.workspace_path
    if hasattr(workspace, 'path'):
        return str(workspace.path)
    if hasattr(workspace, 'root_path'):
        return workspace.root_path
    # Fallback: return string representation (should not normally happen)
    return str(workspace)
