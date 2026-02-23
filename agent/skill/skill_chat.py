"""
Skill Chat Module

Provides ReAct-based streaming execution for skills.
Handles tool calling, prompt building, and script execution for skill chat operations.
"""
import os
import logging
from typing import AsyncGenerator, Any, Dict, Optional, TYPE_CHECKING

from agent.skill.skill_models import Skill
from agent.event.agent_event import AgentEventType

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from agent.event.agent_event import AgentEvent


class SkillChat:
    """
    Handles ReAct-based streaming execution for skills.

    This class manages the chat-style execution of skills using the ReAct framework,
    allowing skills to use tools and execute scripts dynamically.
    """

    def __init__(self, skill_service):
        """
        Initialize the SkillChat handler.

        Args:
            skill_service: The SkillService instance for executing scripts
        """
        self.skill_service = skill_service

    async def chat_stream(
        self,
        skill: Skill,
        user_message: Optional[str] = None,
        workspace: Any = None,
        project: Any = None,
        args: Optional[Dict[str, Any]] = None,
        llm_service: Any = None,
        max_steps: int = 10,
        crew_member_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> AsyncGenerator["AgentEvent", None]:
        """通过 React 流式执行 skill

        Args:
            skill: The Skill object to execute
            user_message: Optional user message/question
            workspace: Any object (optional)
            project: Any object (optional)
            args: Arguments to pass to the skill
            llm_service: Optional LLM service
            max_steps: Maximum number of ReAct steps
            crew_member_name: Name of the crew member calling this skill (for react_type uniqueness)
            conversation_id: Unique conversation/session ID (for react_type uniqueness)

        Yields:
            AgentEvent objects for skill execution progress (including SKILL_START, SKILL_PROGRESS, SKILL_END, SKILL_ERROR)
        """
        from agent.event.agent_event import AgentEvent

        # Handle both string (project_name directly) and object (with project_name attribute) cases
        if isinstance(project, str):
            project_name = project
        else:
            project_name = getattr(project, 'project_name', 'default_project') if project else 'default_project'

        # Generate a unique run_id for this skill execution
        import uuid
        run_id = str(uuid.uuid4())[:8]
        step_id = 0

        # Build unique react_type to prevent checkpoint pollution
        # Format: skill_{skill_name}_{crew_member}_{conversation_id}
        # This ensures different conversations and different crew members are isolated
        if crew_member_name:
            crew_member_part = crew_member_name.lower().replace(' ', '_').replace('-', '_')
        else:
            crew_member_part = 'unknown_crew'

        if conversation_id:
            conversation_part = conversation_id
        else:
            # Generate a unique conversation ID if not provided
            conversation_part = f"conv_{run_id}"

        react_type = f"skill_{skill.name}_{crew_member_part}_{conversation_part}"

        # Determine sender_id and sender_name from crew_member information
        # Use crew_member name for sender info to match crew member event style
        skill_sender_id = crew_member_name if crew_member_name else f"skill_{skill.name}"
        skill_sender_name = crew_member_name if crew_member_name else f"Skill: {skill.name}"

        # Emit SKILL_START event
        from agent.chat.content import SkillContent, SkillExecutionState
        yield AgentEvent.create(
            event_type=AgentEventType.SKILL_START.value,
            project_name=project_name,
            react_type=react_type,
            run_id=run_id,
            step_id=step_id,
            sender_id=skill_sender_id,
            sender_name=skill_sender_name,
            content=SkillContent(
                skill_name=skill.name,
                state=SkillExecutionState.IN_PROGRESS,
                progress_text="Starting execution...",
                title=f"Skill: {skill.name}",
                description=skill.description
            )
        )

        try:
            from agent.react import React
            from agent.tool.tool_service import ToolService

            if llm_service is None:
                from agent.llm.llm_service import LlmService
                llm_service = LlmService(workspace)

            # Build available tool names based on skill type
            tool_service = ToolService()
            available_tool_names = list(tool_service.get_available_tools())

            # Add todo tool for complex task tracking
            available_tool_names.append("todo")

            # Add skill-specific tools based on whether skill has scripts
            if skill.scripts:
                available_tool_names.append("execute_skill_script")
            else:
                available_tool_names.append("execute_generated_code")

            def build_prompt_function(user_question: str) -> str:
                return self._build_skill_react_prompt(
                    skill, user_question, available_tool_names, args
                )

            react_instance = React(
                workspace=workspace,
                project_name=project_name,
                react_type=react_type,
                build_prompt_function=build_prompt_function,
                available_tool_names=available_tool_names,
                llm_service=llm_service,
                max_steps=max_steps,
            )

            # Track tool events to emit skill progress
            tool_count = 0
            executed_tools = []  # Track names of executed tools
            async for event in react_instance.chat_stream(user_message or skill.description):
                yield event
                # Emit SKILL_PROGRESS for each tool event
                if event.event_type in (AgentEventType.TOOL_START.value, AgentEventType.TOOL_PROGRESS.value, AgentEventType.TOOL_END.value):
                    tool_count += 1
                    step_id += 1

                    # Extract tool name from event content if available
                    tool_name = "unknown"
                    if event.content and hasattr(event.content, 'tool_name'):
                        tool_name = event.content.tool_name
                    elif event.payload:
                        tool_name = event.payload.get("tool_name", "unknown")

                    # Add to executed tools list (avoid duplicates)
                    if tool_name != "unknown" and tool_name not in executed_tools:
                        executed_tools.append(tool_name)

                    # Create progress message with tool information
                    if tool_name != "unknown":
                        progress_text = f"Executing tool [{tool_count}] - {tool_name}"
                        description_text = f"Tool {tool_name} execution in progress"
                    else:
                        progress_text = f"{tool_count} tool execution(s) completed"
                        description_text = f"Executed {tool_count} tool(s)"

                    yield AgentEvent.create(
                        event_type=AgentEventType.SKILL_PROGRESS.value,
                        project_name=project_name,
                        react_type=react_type,
                        run_id=run_id,
                        step_id=step_id,
                        sender_id=skill_sender_id,
                        sender_name=skill_sender_name,
                        content=SkillContent(
                            skill_name=skill.name,
                            state=SkillExecutionState.IN_PROGRESS,
                            progress_text=progress_text,
                            progress_percentage=None,
                            title=f"Skill Progress: {skill.name}",
                            description=description_text
                        )
                    )

            # Emit SKILL_END event on successful completion
            step_id += 1

            # Prepare completion message with tool summary
            if executed_tools:
                tools_summary = ", ".join(executed_tools)
                result_text = f"Executed {len(executed_tools)} tool(s): {tools_summary}"
                description_text = f"Completed {len(executed_tools)} tool(s): {tools_summary}"
            else:
                result_text = "Skill execution completed successfully"
                description_text = f"Skill {skill.name} finished execution"

            yield AgentEvent.create(
                event_type=AgentEventType.SKILL_END.value,
                project_name=project_name,
                react_type=react_type,
                run_id=run_id,
                step_id=step_id,
                sender_id=skill_sender_id,
                sender_name=skill_sender_name,
                content=SkillContent(
                    skill_name=skill.name,
                    state=SkillExecutionState.COMPLETED,
                    result=result_text,
                    progress_percentage=100,
                    title=f"Skill Completed: {skill.name}",
                    description=description_text
                )
            )

        except Exception as e:
            logger.error(f"Error in skill chat_stream for '{skill.name}': {e}", exc_info=True)
            # Emit SKILL_ERROR event
            step_id += 1
            from agent.chat.content import SkillContent, SkillExecutionState
            yield AgentEvent.create(
                event_type=AgentEventType.SKILL_ERROR.value,
                project_name=project_name,
                react_type=react_type,
                run_id=run_id,
                step_id=step_id,
                sender_id=skill_sender_id,
                sender_name=skill_sender_name,
                content=SkillContent(
                    skill_name=skill.name,
                    state=SkillExecutionState.ERROR,
                    error_message=str(e),
                    title=f"Skill Error: {skill.name}",
                    description=f"Error executing skill: {skill.name}"
                )
            )

    def _build_skill_react_prompt(self, skill, user_question, available_tool_names, args) -> str:
        """Build the skill-specific ReAct prompt.

        Args:
            skill: The Skill object
            user_question: The user's question/task
            available_tool_names: List of available tool names
            args: Arguments for the skill

        Returns:
            The rendered prompt string
        """
        from agent.prompt.prompt_service import prompt_service
        from agent.tool.tool_service import ToolService

        tool_service = ToolService()
        available_tools = [
            tool_service.get_tool_metadata(name)
            for name in available_tool_names
        ]

        # Build full script paths for the prompt
        script_full_paths = []
        if skill.scripts:
            for script in skill.scripts:
                if os.path.isabs(script):
                    script_full_paths.append(script)
                else:
                    script_full_paths.append(os.path.join(skill.skill_path, script))

        return prompt_service.render_prompt(
            name="skill_react",
            skill={
                'name': skill.name,
                'description': skill.description,
                'knowledge': skill.knowledge,
                'skill_path': skill.skill_path,
                'has_scripts': bool(skill.scripts),
                'script_names': [os.path.basename(s) for s in (skill.scripts or [])],
                'script_full_paths': script_full_paths,
            },
            user_question=user_question or skill.description,
            available_tools=available_tools,
            args=args or {},
        )
