from pathlib import Path

from ...base_tool import BaseTool, ToolMetadata, ToolParameter
from typing import Any, Dict, TYPE_CHECKING, Optional, AsyncGenerator
import logging
from ....plan.plan_service import PlanService
from ....plan.plan_models import PlanTask
from datetime import datetime

# Tool directory for metadata loading
_tool_dir = Path(__file__).parent

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ....tool_context import ToolContext
    from agent.event.agent_event import AgentEvent


class CreatePlanTool(BaseTool):
    """
    Tool to create a plan execution for a project.
    """

    def __init__(self):
        super().__init__(
            name="create_plan",
            description="Create a plan execution for the current project"
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
        Execute the plan creation using PlanService.

        Args:
            parameters: Parameters for the plan including title, description, tasks
            context: ToolContext containing workspace and project info
            project_name: Project name for event tracking
            react_type: React type for event tracking
            run_id: Run ID for event tracking
            step_id: Step ID for event tracking
            sender_id: ID of the event sender
            sender_name: Display name of the event sender

        Yields:
            ReactEvent objects with the created plan details
        """
        # Extract required parameters
        title = parameters.get('title', 'Untitled Plan')
        description = parameters.get('description', 'No description provided')
        raw_tasks = parameters.get('tasks', [])

        # Extract project information from context
        workspace = context.workspace if context else None
        project_name = context.project_name if context else 'Unknown Project'

        # Get PlanService instance for this workspace/project combination
        plan_service = PlanService.get_instance(workspace, project_name)

        # Convert raw tasks to PlanTask objects
        plan_tasks = []
        for idx, raw_task in enumerate(raw_tasks):
            if isinstance(raw_task, dict):
                task_id = raw_task.get('id', f'task_{idx}_{int(datetime.now().timestamp())}')
                task_name = raw_task.get('name', raw_task.get('title', f'Task {idx+1}'))
                task_description = raw_task.get('description', raw_task.get('desc', 'No description'))
                task_title = raw_task.get('title', raw_task.get('role', 'other'))
                task_params = raw_task.get('parameters', raw_task.get('params', {}))
                task_needs = raw_task.get('needs', raw_task.get('dependencies', []))

                plan_task = PlanTask(
                    id=task_id,
                    name=task_name,
                    description=task_description,
                    title=task_title,
                    parameters=task_params,
                    needs=task_needs
                )
                plan_tasks.append(plan_task)
            else:
                # Handle case where raw_task is not a dict
                task_id = f'task_{idx}_{int(datetime.now().timestamp())}'
                plan_task = PlanTask(
                    id=task_id,
                    name=f'Task {idx+1}',
                    description=str(raw_task) if raw_task else 'No description',
                    title='other',
                    parameters={}
                )
                plan_tasks.append(plan_task)

        try:
            # Create the plan using PlanService
            plan = plan_service.create_plan(
                project_name=project_name,
                name=title,
                description=description,
                tasks=plan_tasks
            )

            # Return the created plan details
            result = {
                'id': plan.id,
                'title': plan.name,
                'description': plan.description,
                'tasks': [self._convert_task_to_dict(task) for task in plan.tasks],
                'created_at': plan.created_at.isoformat(),
                'project': plan.project_name,
                'status': plan.status.value
            }

            yield self._create_event(
                "tool_end",
                project_name,
                react_type,
                run_id,
                step_id,
                ok=True,
                result=result
            )

        except Exception as e:
            logger.error(f"Error creating plan: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    def _convert_task_to_dict(self, task: PlanTask) -> Dict[str, Any]:
        """Convert a PlanTask object to a dictionary."""
        return {
            'id': task.id,
            'name': task.name,
            'description': task.description,
            'title': task.title,
            'parameters': task.parameters,
            'needs': task.needs,
            'status': task.status.value,
            'created_at': task.created_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'error_message': task.error_message
        }
