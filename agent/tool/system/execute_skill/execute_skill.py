from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING, AsyncGenerator
import logging
from ...base_tool import BaseTool, ToolMetadata, ToolParameter

# Tool directory for metadata loading
_tool_dir = Path(__file__).parent

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ....tool_context import ToolContext
    from agent.event.agent_event import AgentEvent


class ExecuteSkillTool(BaseTool):
    """
    Tool to execute a skill through SkillService's chat_stream method.
    This is a bridge tool that allows React to execute skills using ReAct.
    """

    def __init__(self):
        super().__init__(
            name="execute_skill",
            description="Execute a skill through ReAct-based chat stream"
        )
        # Set tool directory for metadata loading from tool.md
        self._tool_dir = _tool_dir

    def _get_crew_members_info(self, context: Optional["ToolContext"]) -> Optional[str]:
        """Get formatted information about all crew members in the project.

        Args:
            context: ToolContext containing workspace and project info

        Returns:
            A formatted string containing information about all crew members,
            or None if no crew members are available.
        """
        try:
            if not context or not context.project:
                return None

            from agent.crew.crew_service import CrewService
            from agent.crew.crew_title import sort_crew_members_by_title_importance

            crew_service = CrewService()
            crew_members_dict = crew_service.get_project_crew_members(context.project)

            if not crew_members_dict:
                return None

            # Sort crew members by title importance
            sorted_members = sort_crew_members_by_title_importance(crew_members_dict)

            member_info_list = []
            for member in sorted_members:
                # Format each member's information
                role = member.config.metadata.get('crew_title', member.config.name) if member.config.metadata else member.config.name
                skills_str = ", ".join(member.config.skills) if member.config.skills else "None"
                description = member.config.description or "No description available"

                member_info = f"- **{member.config.name}** (role: {role})\n  - Description: {description}\n  - Skills: {skills_str}"
                member_info_list.append(member_info)

            if not member_info_list:
                return None

            return "\n\n".join(member_info_list)

        except Exception as e:
            logger.debug(f"Could not get crew members info: {e}")
            return None

    # metadata() is now handled by BaseTool using tool.md
    # No need to override here

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional["ToolContext"] = None,
        project_name: str = "",
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
    ) -> AsyncGenerator["AgentEvent", None]:
        """
        Execute a skill using SkillService.chat_stream().

        This method uses SkillService's ReAct-based chat stream to execute skills,
        which allows the skill to use tools and have multi-step reasoning.

        Args:
            parameters: Parameters including skill_name and prompt
            context: ToolContext containing workspace and project info
            project_name: Project name for event tracking
            react_type: React type for event tracking
            run_id: Run ID for event tracking
            step_id: Step ID for event tracking
            sender_id: ID of the event sender
            sender_name: Display name of the event sender

        Yields:
            ReactEvent objects with progress updates and results
        """
        workspace = context.workspace if context else None

        if not workspace:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                sender_id,
                sender_name,
                error="Workspace not available in context"
            )
            return

        from agent.skill.skill_service import SkillService
        from agent.event.agent_event import AgentEvent, AgentEventType

        skill_service = SkillService(workspace)

        skill_name = parameters.get("skill_name")
        prompt = parameters.get("prompt") or parameters.get("message")
        max_steps = parameters.get("max_steps", 10)

        if not skill_name:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                sender_id,
                sender_name,
                error="skill_name is required"
            )
            return

        if not prompt:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                sender_id,
                sender_name,
                error="prompt is required"
            )
            return

        # Get language from context for skill loading
        language = None
        if context and context.project and hasattr(context.project, 'get_language'):
            language = context.project.get_language()

        skill = skill_service.get_skill(skill_name, language=language)
        if not skill:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                sender_id,
                sender_name,
                error=f"Skill '{skill_name}' not found"
            )
            return

        try:
            crew_member_name = sender_id if sender_id else None
            conversation_id = run_id if run_id else None

            # Get crew members info for team context
            crew_members_info = self._get_crew_members_info(context)

            final_response = None
            has_error = False
            async for event in skill_service.chat_stream(
                    skill=skill,
                    user_message=prompt,
                    workspace=workspace,
                    project=context.project_name if context else None,
                    llm_service=None,
                    max_steps=max_steps,
                    crew_member_name=crew_member_name,
                    conversation_id=conversation_id,
                    run_id=run_id,
                    crew_members=crew_members_info,
            ):
                if event.event_type == AgentEventType.FINAL:
                    if event.content and hasattr(event.content, 'text'):
                        final_response = event.content.text
                    elif event.payload:
                        final_response = event.payload.get("final_response")
                    # Don't return yet - continue iterating so SKILL_END can be forwarded
                    continue
                elif event.event_type == AgentEventType.ERROR:
                    if event.content and hasattr(event.content, 'error_message'):
                        error = event.content.error_message
                    elif event.payload:
                        error = event.payload.get("error", "Unknown error")
                    else:
                        error = "Unknown error"
                    yield self._create_event(
                        "error",
                        project_name,
                        react_type,
                        run_id,
                        step_id,
                        sender_id,
                        sender_name,
                        error=error
                    )
                    has_error = True
                    return
                else:
                    yield AgentEvent.create(
                        event_type=event.event_type,
                        project_name=event.project_name or project_name,
                        react_type=event.react_type or react_type,
                        run_id=event.run_id or run_id,
                        step_id=event.step_id or step_id,
                        sender_id=sender_id,
                        sender_name=sender_name,
                        content=event.content
                    )

            if not has_error:
                yield self._create_event(
                    "tool_end",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    sender_id,
                    sender_name,
                    ok=True,
                    result=final_response or "Skill execution completed"
                )

        except Exception as e:
            logger.error(f"Error executing skill '{parameters.get('skill_name', 'unknown')}': {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                sender_id,
                sender_name,
                error=f"Error executing skill: {str(e)}"
            )
