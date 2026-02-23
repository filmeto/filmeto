from pathlib import Path
from ...base_tool import BaseTool, ToolMetadata, ToolParameter
from typing import Any, Dict, Optional, TYPE_CHECKING, AsyncGenerator
import logging
from agent.crew.crew_service import CrewService

# Tool directory for metadata loading
_tool_dir = Path(__file__).parent

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ....tool_context import ToolContext
    from agent.event.agent_event import AgentEvent


class GetProjectCrewMembersTool(BaseTool):
    """
    Tool to get the list of crew members in a project.
    """

    def __init__(self):
        super().__init__(
            name="get_project_crew_members",
            description="Get the list of crew members in the current project"
        )
        # Set tool directory for metadata loading from tool.md
        self._tool_dir = _tool_dir

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
        Execute the crew member retrieval using CrewService.

        Args:
            parameters: Additional parameters (currently unused)
            context: ToolContext containing workspace and project info
            project_name: Project name for event tracking
            react_type: React type for event tracking
            run_id: Run ID for event tracking
            step_id: Step ID for event tracking
            sender_id: ID of the event sender
            sender_name: Display name of the event sender

        Yields:
            ReactEvent objects with the crew members list
        """
        try:
            # Extract project information from context
            workspace = context.workspace if context else None

            if not workspace:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="Workspace not available in context"
                )
                return

            # Get the project from workspace
            project = workspace.get_project()

            # Initialize CrewService
            crew_service = CrewService()

            # Get crew members for the project using CrewService
            crew_members_dict = crew_service.get_project_crew_members(project)

            # Convert CrewMember objects to dictionaries
            crew_members_list = []
            for name, crew_member in crew_members_dict.items():
                member_info = {
                    "id": name,  # Using name as ID since CrewMember doesn't have a separate ID
                    "name": crew_member.config.name,
                    "role": getattr(crew_member.config, 'crew_title', 'member'),  # Using crew_title as role
                    "description": crew_member.config.description,
                    "soul": crew_member.config.soul or "",  # The associated soul name
                    "skills": crew_member.config.skills,  # List of skills
                    "model": crew_member.config.model,  # Model used by the crew member
                    "temperature": crew_member.config.temperature,  # Temperature setting
                    "max_steps": crew_member.config.max_steps,  # Max steps for the crew member
                    "color": crew_member.config.color,  # Color for UI representation
                    "icon": crew_member.config.icon  # Icon for UI representation
                }
                crew_members_list.append(member_info)

            yield self._create_event(
                "tool_end",
                project_name,
                react_type,
                run_id,
                step_id,
                ok=True,
                result=crew_members_list
            )
        except Exception as e:
            logger.error(f"Error getting project crew members: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )
