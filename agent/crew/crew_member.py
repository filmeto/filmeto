import os
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional, TYPE_CHECKING

import yaml

from agent.chat.agent_chat_message import AgentMessage, StructureContent
from agent.chat.agent_chat_signals import AgentChatSignals
from agent.chat.agent_chat_types import ContentType, MessageType
from agent.llm.llm_service import LlmService
from agent.plan.service import PlanService
from agent.skill.skill_service import SkillService, Skill
from agent.soul import soul_service as soul_service_instance, SoulService
from agent.prompt.prompt_service import prompt_service

if TYPE_CHECKING:
    from agent.event.agent_event import AgentEvent
    from agent.react.types import AgentEventType


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
        self.llm_service = llm_service or LlmService(workspace)
        self.skill_service = skill_service or SkillService(workspace)
        self.plan_service = plan_service or PlanService()
        # Set the workspace if available to ensure proper plan storage location
        if workspace:
            self.plan_service.set_workspace(workspace)
        self.soul_service = soul_service or self._build_soul_service(project)
        self.conversation_history: List[Dict[str, str]] = []
        self.signals = AgentChatSignals()

    async def chat_stream(
        self,
        message: str,
        plan_id: Optional[str] = None,
    ) -> AsyncIterator["AgentEvent"]:
        """
        Stream chat responses as ReactEvent objects.

        Args:
            message: The user message to process
            plan_id: Optional plan ID for context

        Yields:
            ReactEvent: Events from the ReAct execution process
        """
        from agent.react import react_service, AgentEventType, AgentEvent

        if not self.llm_service.validate_config():
            yield AgentEvent.error(
                error_message="LLM service is not configured.",
                project_name=self.project_name,
                react_type=self.config.name,
                run_id=getattr(self, "_run_id", ""),
                sender_id=self.config.name,
                sender_name=self.config.name,
            )
            return

        def build_prompt_function(user_question: str) -> str:
            return self._build_user_prompt(user_question, plan_id=plan_id)

        # Build available tool names - use execute_skill as the tool
        available_tool_names = ["execute_skill", "todo_write"]

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
                yield enhanced_event
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
                yield enhanced_event
                break
            else:
                # Yield all other events (LLM_THINKING, TOOL_START, TOOL_PROGRESS, TOOL_END, etc.)
                yield enhanced_event

        if not saw_event:
            return

        if final_response is None:
            # Create an error event if we didn't get a final response
            yield AgentEvent.error(
                error_message="Reached max steps without a final response.",
                project_name=self.project_name,
                react_type=self.config.name,
                run_id=getattr(self, "_run_id", ""),
                sender_id=self.config.name,
                sender_name=self.config.name,
            )
            return

    def _build_user_prompt(self, user_question: str, plan_id: Optional[str] = None) -> str:
        """Build a user prompt that embeds the user's question into the react_base template.

        Args:
            user_question: The user's question(s). May contain multiple questions separated by newlines.
            plan_id: Optional plan ID for context.
        """
        soul_content = self._get_formatted_soul_prompt()

        # Prepare skills as structured data for the template
        skills_list = self._get_skills_as_structured_list()

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
        )

        # If the base prompt template is not available, fall back to the original method
        if user_prompt is None:
            prompt_sections = [
                "You are a ReAct-style crew member.",
                f"Crew member name: {self.config.name}.",
            ]
            if self.config.description:
                prompt_sections.append(f"Role description: {self.config.description}")
            if self.config.prompt:
                prompt_sections.append(self.config.prompt.strip())

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

        base_prompt = prompt_service.render_prompt(
            name="crew_member_react",
            title="crew member",
            agent_name=self.config.name,
            role_description=f"Role description: {self.config.description}" if self.config.description else "",
            soul_profile=soul_content,
            skills_list=skills_list,
            context_info=f"Active plan id: {plan_id}." if plan_id else f"Project name: {self.project_name}." if self.project_name else "",
        )

        # If the base prompt template is not available, fall back to the original method
        if base_prompt is None:
            prompt_sections = [
                "You are a ReAct-style crew member.",
                f"Crew member name: {self.config.name}.",
            ]
            if self.config.description:
                prompt_sections.append(f"Role description: {self.config.description}")
            if self.config.prompt:
                prompt_sections.append(self.config.prompt.strip())

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
        if not self.config.skills:
            # If no skills are configured for this crew member, fall back to all available skills
            return self._get_all_available_skills_as_structured_list()

        skills_list = []
        for name in self.config.skills:
            skill = self.skill_service.get_skill(name)
            if not skill:
                continue  # Skip unavailable skills

            # Extract usage criteria from knowledge if available
            usage_criteria = ""
            if skill.knowledge:
                knowledge_lines = skill.knowledge.split('\n')
                for line in knowledge_lines[:10]:  # Check first 10 lines for use cases
                    line_lower = line.lower().strip()
                    if any(keyword in line_lower for keyword in ['when', 'use', 'should', 'can', 'capability', 'feature']):
                        if any(char in line for char in ['-', '*', '•']):
                            usage_criteria = line.strip(' -•*')
                            break
                if not usage_criteria:
                    usage_criteria = skill.description

            skills_list.append({
                'name': skill.name,
                'description': skill.description,
                'usage_criteria': usage_criteria,
                'parameters': [
                    {
                        'name': param.name,
                        'type': param.param_type,
                        'required': param.required,
                        'default': param.default,
                        'description': param.description
                    } for param in skill.parameters
                ],
                'example_call': skill.get_example_call()
                # Exclude knowledge field to keep the prompt concise
            })

        return skills_list

    def _get_all_available_skills_as_structured_list(self) -> list:
        """Get all available skills as a structured list for advanced templating."""
        all_skills = self.skill_service.get_all_skills()

        skills_list = []
        for skill in all_skills:  # all_skills is a list, not a dict
            # Extract usage criteria from knowledge if available
            usage_criteria = ""
            if skill.knowledge:
                knowledge_lines = skill.knowledge.split('\n')
                for line in knowledge_lines[:10]:  # Check first 10 lines for use cases
                    line_lower = line.lower().strip()
                    if any(keyword in line_lower for keyword in ['when', 'use', 'should', 'can', 'capability', 'feature']):
                        if any(char in line for char in ['-', '*', '•']):
                            usage_criteria = line.strip(' -•*')
                            break
                if not usage_criteria:
                    usage_criteria = skill.description

            skills_list.append({
                'name': skill.name,
                'description': skill.description,
                'usage_criteria': usage_criteria,
                'parameters': [
                    {
                        'name': param.name,
                        'type': param.param_type,
                        'required': param.required,
                        'default': param.default,
                        'description': param.description
                    } for param in skill.parameters
                ],
                'example_call': skill.get_example_call()
                # Exclude knowledge field to keep the prompt concise
            })

        return skills_list

    def _get_formatted_soul_prompt(self) -> str:
        """Get formatted soul prompt for use in system prompt."""
        if not self.config.soul:
            return ""
        soul = self.soul_service.get_soul_by_name(self.project_name, self.config.soul)
        if not soul:
            return f"Soul '{self.config.soul}' not found."
        if soul.knowledge:
            return soul.knowledge
        return f"Soul '{self.config.soul}' has no prompt content."

    def _get_soul_prompt(self) -> str:
        if not self.config.soul:
            return ""
        soul = self.soul_service.get_soul_by_name(self.project_name, self.config.soul)
        if not soul:
            return f"Soul '{self.config.soul}' not found."
        if soul.knowledge:
            return soul.knowledge
        return f"Soul '{self.config.soul}' has no prompt content."

    def _format_skills_prompt(self) -> str:
        if not self.config.skills:
            # If no skills are configured for this crew member, fall back to all available skills
            return self._get_all_available_skills_prompt()

        details = []
        missing = []
        for name in self.config.skills:
            skill = self.skill_service.get_skill(name)
            if not skill:
                missing.append(name)
                continue
            details.append(_format_skill_entry_detailed(skill))

        if not details:
            # If none of the configured skills are available, fall back to all available skills
            return self._get_all_available_skills_prompt()
        else:
            skills_section = (
                "## Available Skills\n\n"
                "You have access to the following skills. Review each skill's purpose and parameters to decide when to use it.\n\n"
                + "\n\n".join(details)
            )

        if missing:
            skills_section += f"\n\nNote: The following skills are configured but not available: {', '.join(missing)}"

        return skills_section

    def _get_all_available_skills_prompt(self) -> str:
        """Get a prompt with all available skills in the project as a fallback."""
        all_skills = self.skill_service.get_all_skills()

        if not all_skills:
            return "Available skills: none.\nYou cannot call any skills."

        details = []
        for skill in all_skills:  # all_skills is a list, not a dict
            details.append(_format_skill_entry_detailed(skill))

        if not details:
            return "Available skills: none.\nYou cannot call any skills."

        return (
            "## Available Skills\n\n"
            "You have access to the following skills. Review each skill's purpose and parameters to decide when to use it.\n\n"
            + "\n\n".join(details)
        )



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

    # Add usage criteria to help LLM decide when to use this skill
    lines.append("**When to use this skill**: This skill should be used when:")
    if skill.knowledge:
        # Extract key capabilities from the knowledge section
        knowledge_lines = skill.knowledge.split('\n')
        # Look for lines that start with bullet points or keywords indicating use cases
        use_case_found = False
        for line in knowledge_lines[:10]:  # Check first 10 lines for use cases
            line_lower = line.lower().strip()
            if any(keyword in line_lower for keyword in ['when', 'use', 'should', 'can', 'capability', 'feature']):
                if any(char in line for char in ['-', '*', '•']):
                    lines.append(f"  - {line.strip(' -•*')}")
                    use_case_found = True
        if not use_case_found:
            lines.append(f"  - {skill.description}")
    else:
        lines.append(f"  - {skill.description}")
    lines.append("")

    # Add parameters
    if skill.parameters:
        lines.append("**Parameters**:")
        for param in skill.parameters:
            req_str = "required" if param.required else "optional"
            default_str = f", default: {param.default}" if param.default is not None else ""
            lines.append(f"  - `{param.name}` ({param.param_type}, {req_str}{default_str}): {param.description}")
        lines.append("")

    # Add example call
    lines.append("**Example call**:")
    lines.append("```json")
    lines.append(skill.get_example_call())
    lines.append("```")

    # Add knowledge snippet if available
    if skill.knowledge:
        # Extract just the capability section
        knowledge_preview = skill.knowledge[:300]
        if len(skill.knowledge) > 300:
            knowledge_preview += "..."
        lines.append("")
        lines.append(f"**Additional Details**: {knowledge_preview}")

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
