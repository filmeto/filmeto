"""CrewMember tool for managing crew members in the project."""
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING, AsyncGenerator
import logging

from ...base_tool import BaseTool, ToolMetadata, ToolParameter
from agent.crew.crew_service import CrewService

# Tool directory for metadata loading
_tool_dir = Path(__file__).parent

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ....tool_context import ToolContext
    from agent.event.agent_event import AgentEvent


class CrewMemberTool(BaseTool):
    """
    Tool for managing crew members in the Filmeto project.

    This tool provides CRUD operations for crew members:
    - Create: Create a new crew member
    - Delete: Remove a crew member by name
    - Update: Update an existing crew member's information
    - Get: Retrieve information about a specific crew member
    - List: List all crew members in the project
    """

    def __init__(self):
        super().__init__(
            name="crew_member",
            description="Manage crew members in the project - create, delete, update, get, and list crew members"
        )
        # Set tool directory for metadata loading from tool.md
        self._tool_dir = _tool_dir
        self._crew_service = CrewService()

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
        Execute the crew_member tool asynchronously.

        Args:
            parameters: Dictionary containing:
                - operation (str): Operation type (create, delete, update, get, list)
                - name (str, optional): Crew member name for create, delete, update, get
                - data (dict, optional): Crew member data for create/update operations
            context: ToolContext containing workspace and project info
            project_name: Project name for event tracking
            react_type: React type for event tracking
            run_id: Run ID for event tracking
            step_id: Step ID for event tracking
            sender_id: ID of the event sender
            sender_name: Display name of the event sender

        Yields:
            AgentEvent objects with progress updates and results
        """
        try:
            operation = parameters.get("operation")
            if not operation:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="operation parameter is required"
                )
                return

            # Get project from context
            project = self._get_project(context)
            if project is None:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="Could not access project. Make sure you are in a valid project context."
                )
                return

            # Route to appropriate operation handler
            if operation == "create":
                async for event in self._handle_create(project, parameters, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "delete":
                async for event in self._handle_delete(project, parameters, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "update":
                async for event in self._handle_update(project, parameters, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "get":
                async for event in self._handle_get(project, parameters, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "list":
                async for event in self._handle_list(project, project_name, react_type, run_id, step_id):
                    yield event
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Unknown operation: {operation}. Valid operations: create, delete, update, get, list"
                )

        except Exception as e:
            logger.error(f"Error in crew_member tool: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    def _get_project(self, context: Optional["ToolContext"]) -> Optional[Any]:
        """Get the project object from context."""
        if context is None:
            return None
        return context.workspace if hasattr(context, 'workspace') else None

    def _crew_member_to_dict(self, crew_member: 'CrewMember') -> Dict[str, Any]:
        """Convert a CrewMember object to a dictionary."""
        return {
            "id": crew_member.config.name,
            "name": crew_member.config.name,
            "role": getattr(crew_member.config, 'crew_title', 'member'),
            "description": crew_member.config.description,
            "soul": crew_member.config.soul or "",
            "skills": crew_member.config.skills,
            "model": crew_member.config.model,
            "temperature": crew_member.config.temperature,
            "max_steps": crew_member.config.max_steps,
            "color": crew_member.config.color,
            "icon": crew_member.config.icon
        }

    async def _handle_create(
        self,
        project: Any,
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle create operation."""
        try:
            data = parameters.get("data")
            if not data:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="data parameter is required for create operation"
                )
                return

            # Validate required fields
            if not data.get("name"):
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="name is required in data parameter"
                )
                return

            file_path = self._crew_service.write_project_crew_member(project, data)

            if file_path:
                yield self._create_event(
                    "tool_progress",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    result=f"Created crew member '{data.get('name')}' at {file_path}"
                )

                yield self._create_event(
                    "tool_end",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    ok=True,
                    result={
                        "operation": "create",
                        "success": True,
                        "name": data.get("name"),
                        "file_path": file_path,
                        "message": f"Successfully created crew member '{data.get('name')}'"
                    }
                )
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="Failed to create crew member"
                )
        except Exception as e:
            logger.error(f"Error creating crew member: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    async def _handle_delete(
        self,
        project: Any,
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle delete operation."""
        try:
            name = parameters.get("name")
            if not name:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="name parameter is required for delete operation"
                )
                return

            success = self._crew_service.delete_project_crew_member(project, name)

            if success:
                yield self._create_event(
                    "tool_progress",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    result=f"Deleted crew member '{name}'"
                )

                yield self._create_event(
                    "tool_end",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    ok=True,
                    result={
                        "operation": "delete",
                        "success": True,
                        "name": name,
                        "message": f"Successfully deleted crew member '{name}'"
                    }
                )
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Failed to delete crew member '{name}'. Crew member not found."
                )
        except Exception as e:
            logger.error(f"Error deleting crew member: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    async def _handle_update(
        self,
        project: Any,
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle update operation."""
        try:
            name = parameters.get("name")
            data = parameters.get("data")

            if not name:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="name parameter is required for update operation"
                )
                return

            if not data:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="data parameter is required for update operation"
                )
                return

            success = self._crew_service.update_project_crew_member(project, name, data)

            if success:
                yield self._create_event(
                    "tool_progress",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    result=f"Updated crew member '{name}'"
                )

                yield self._create_event(
                    "tool_end",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    ok=True,
                    result={
                        "operation": "update",
                        "success": True,
                        "name": name,
                        "message": f"Successfully updated crew member '{name}'"
                    }
                )
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Failed to update crew member '{name}'. Crew member not found."
                )
        except Exception as e:
            logger.error(f"Error updating crew member: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    async def _handle_get(
        self,
        project: Any,
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle get operation."""
        try:
            name = parameters.get("name")
            if not name:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="name parameter is required for get operation"
                )
                return

            crew_member = self._crew_service.get_crew_member(project, name)

            if crew_member:
                member_dict = self._crew_member_to_dict(crew_member)

                yield self._create_event(
                    "tool_end",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    ok=True,
                    result={
                        "operation": "get",
                        "success": True,
                        "crew_member": member_dict,
                        "message": f"Retrieved crew member '{name}'"
                    }
                )
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Crew member '{name}' not found"
                )
        except Exception as e:
            logger.error(f"Error getting crew member: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    async def _handle_list(
        self,
        project: Any,
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle list operation."""
        try:
            crew_members_dict = self._crew_service.get_project_crew_members(project)

            crew_members_list = []
            for name, crew_member in crew_members_dict.items():
                member_dict = self._crew_member_to_dict(crew_member)
                crew_members_list.append(member_dict)

            total_count = len(crew_members_list)
            message = f"Found {total_count} crew member(s)"

            yield self._create_event(
                "tool_end",
                project_name,
                react_type,
                run_id,
                step_id,
                ok=True,
                result={
                    "operation": "list",
                    "success": True,
                    "crew_members": crew_members_list,
                    "total_count": total_count,
                    "message": message
                }
            )
        except Exception as e:
            logger.error(f"Error listing crew members: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )
