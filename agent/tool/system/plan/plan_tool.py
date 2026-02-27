"""Plan tool for managing plans in the project."""
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING, AsyncGenerator
import logging
from datetime import datetime

from ...base_tool import BaseTool, ToolMetadata, ToolParameter
from agent.plan.plan_service import PlanService
from agent.plan.plan_models import PlanTask
from agent.event.agent_event import AgentEvent, AgentEventType

# Tool directory for metadata loading
_tool_dir = Path(__file__).parent

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ....tool_context import ToolContext


class PlanTool(BaseTool):
    """
    Tool for managing plans in the Filmeto project.

    This tool provides CRUD operations for plans:
    - Create: Create a new plan with tasks
    - Delete: Remove a plan by ID
    - Update: Update an existing plan's information
    - Get: Retrieve information about a specific plan
    - List: List all plans in the project
    """

    def __init__(self):
        super().__init__(
            name="plan",
            description="Manage plans in the project - create, delete, update, get, and list plans"
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
        Execute the plan tool asynchronously.

        Args:
            parameters: Dictionary containing:
                - operation (str): Operation type (create, delete, update, get, list)
                - plan_id (str, optional): Plan ID for delete, update, get operations
                - title (str, optional): Plan title for create/update operations
                - description (str, optional): Plan description for create/update operations
                - tasks (list, optional): Task list for create/update operations
                - append_tasks (list, optional): Additional tasks to append for update operation
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

            # Get workspace and project_name from context
            workspace = context.workspace if context else None
            effective_project_name = context.project_name if context else project_name

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

            if not effective_project_name:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="Project name not available"
                )
                return

            # Get PlanService instance
            plan_service = PlanService.get_instance(workspace, effective_project_name)

            # Route to appropriate operation handler
            if operation == "create":
                async for event in self._handle_create(
                    plan_service, parameters, effective_project_name, project_name, react_type, run_id, step_id
                ):
                    yield event
            elif operation == "delete":
                async for event in self._handle_delete(
                    plan_service, parameters, effective_project_name, project_name, react_type, run_id, step_id
                ):
                    yield event
            elif operation == "update":
                async for event in self._handle_update(
                    plan_service, parameters, effective_project_name, project_name, react_type, run_id, step_id
                ):
                    yield event
            elif operation == "get":
                async for event in self._handle_get(
                    plan_service, parameters, effective_project_name, project_name, react_type, run_id, step_id
                ):
                    yield event
            elif operation == "list":
                async for event in self._handle_list(
                    plan_service, parameters, effective_project_name, project_name, react_type, run_id, step_id
                ):
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
            logger.error(f"Error in plan tool: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    def _create_plan_event(
        self,
        event_type: str,
        plan: 'Plan',
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int,
        operation: str = "create"
    ) -> AgentEvent:
        """Create a plan-related AgentEvent with PlanContent.

        Args:
            event_type: Type of event (plan_created, plan_updated, etc.)
            plan: The Plan model object
            project_name: Project name for event tracking
            react_type: React type for event tracking
            run_id: Run ID for event tracking
            step_id: Step ID for event tracking
            operation: Operation type (create, update, get, list, delete)

        Returns:
            AgentEvent with PlanContent
        """
        from agent.chat.content import PlanContent

        content = PlanContent.from_plan(plan, operation=operation)

        return AgentEvent.create(
            event_type=event_type,
            project_name=project_name,
            react_type=react_type,
            run_id=run_id,
            step_id=step_id,
            content=content
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

    def _convert_plan_to_dict(self, plan: 'Plan') -> Dict[str, Any]:
        """Convert a Plan object to a dictionary."""
        return {
            'id': plan.id,
            'title': plan.name,
            'description': plan.description,
            'tasks': [self._convert_task_to_dict(task) for task in plan.tasks],
            'created_at': plan.created_at.isoformat(),
            'project': plan.project_name,
            'status': plan.status.value,
            'metadata': plan.metadata
        }

    def _parse_raw_tasks(self, raw_tasks: list) -> list:
        """Convert raw task data to PlanTask objects."""
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
        return plan_tasks

    async def _handle_create(
        self,
        plan_service: PlanService,
        parameters: Dict[str, Any],
        effective_project_name: str,
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle create operation."""
        try:
            title = parameters.get('title', 'Untitled Plan')
            description = parameters.get('description', 'No description provided')
            raw_tasks = parameters.get('tasks', [])

            # Convert raw tasks to PlanTask objects
            plan_tasks = self._parse_raw_tasks(raw_tasks)

            # Create the plan using PlanService
            plan = plan_service.create_plan(
                project_name=effective_project_name,
                name=title,
                description=description,
                tasks=plan_tasks
            )

            result = self._convert_plan_to_dict(plan)

            yield self._create_event(
                "tool_progress",
                project_name,
                react_type,
                run_id,
                step_id,
                result=f"Created plan '{title}' with ID {plan.id}"
            )

            # Send PLAN_CREATED event with PlanContent
            yield self._create_plan_event(
                event_type=AgentEventType.PLAN_CREATED.value,
                plan=plan,
                project_name=project_name,
                react_type=react_type,
                run_id=run_id,
                step_id=step_id,
                operation="create"
            )

            # Keep tool_end for backward compatibility
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
                    "plan": result,
                    "message": f"Successfully created plan '{title}' with ID {plan.id}"
                }
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

    async def _handle_delete(
        self,
        plan_service: PlanService,
        parameters: Dict[str, Any],
        effective_project_name: str,
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle delete operation."""
        try:
            plan_id = parameters.get("plan_id")
            if not plan_id:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="plan_id parameter is required for delete operation"
                )
                return

            success = plan_service.delete_plan(effective_project_name, plan_id)

            if success:
                yield self._create_event(
                    "tool_progress",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    result=f"Deleted plan with ID {plan_id}"
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
                        "plan_id": plan_id,
                        "message": f"Successfully deleted plan with ID {plan_id}"
                    }
                )
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Failed to delete plan with ID {plan_id}. Plan not found."
                )
        except Exception as e:
            logger.error(f"Error deleting plan: {e}", exc_info=True)
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
        plan_service: PlanService,
        parameters: Dict[str, Any],
        effective_project_name: str,
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle update operation."""
        try:
            plan_id = parameters.get("plan_id")
            if not plan_id:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="plan_id parameter is required for update operation"
                )
                return

            title = parameters.get('title')
            description = parameters.get('description')
            raw_tasks = parameters.get('tasks')
            raw_append_tasks = parameters.get('append_tasks')

            # Prepare task parameters
            plan_tasks = self._parse_raw_tasks(raw_tasks) if raw_tasks else None
            append_tasks = self._parse_raw_tasks(raw_append_tasks) if raw_append_tasks else None

            # Update the plan using PlanService
            plan = plan_service.update_plan(
                project_name=effective_project_name,
                plan_id=plan_id,
                name=title,
                description=description,
                tasks=plan_tasks,
                append_tasks=append_tasks
            )

            if plan:
                result = self._convert_plan_to_dict(plan)

                yield self._create_event(
                    "tool_progress",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    result=f"Updated plan with ID {plan_id}"
                )

                # Send PLAN_UPDATED event with PlanContent
                yield self._create_plan_event(
                    event_type=AgentEventType.PLAN_UPDATED.value,
                    plan=plan,
                    project_name=project_name,
                    react_type=react_type,
                    run_id=run_id,
                    step_id=step_id,
                    operation="update"
                )

                # Keep tool_end for backward compatibility
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
                        "plan": result,
                        "message": f"Successfully updated plan with ID {plan_id}"
                    }
                )
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Failed to update plan with ID {plan_id}. Plan not found."
                )
        except Exception as e:
            logger.error(f"Error updating plan: {e}", exc_info=True)
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
        plan_service: PlanService,
        parameters: Dict[str, Any],
        effective_project_name: str,
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle get operation."""
        try:
            plan_id = parameters.get("plan_id")
            if not plan_id:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="plan_id parameter is required for get operation"
                )
                return

            plan = plan_service.load_plan(effective_project_name, plan_id)

            if plan:
                result = self._convert_plan_to_dict(plan)

                # Send PLAN event with PlanContent for UI rendering
                yield self._create_plan_event(
                    event_type=AgentEventType.PLAN_UPDATED.value,
                    plan=plan,
                    project_name=project_name,
                    react_type=react_type,
                    run_id=run_id,
                    step_id=step_id,
                    operation="get"
                )

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
                        "plan": result,
                        "message": f"Retrieved plan with ID {plan_id}"
                    }
                )
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Plan with ID {plan_id} not found"
                )
        except Exception as e:
            logger.error(f"Error getting plan: {e}", exc_info=True)
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
        plan_service: PlanService,
        parameters: Dict[str, Any],
        effective_project_name: str,
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle list operation."""
        try:
            plans = plan_service.get_all_plans_for_project(effective_project_name)

            plans_list = [self._convert_plan_to_dict(plan) for plan in plans]
            total_count = len(plans_list)

            # Sort by creation date, most recent first
            plans_list.sort(key=lambda p: p['created_at'], reverse=True)

            message = f"Found {total_count} plan(s)"

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
                    "plans": plans_list,
                    "total_count": total_count,
                    "message": message
                }
            )
        except Exception as e:
            logger.error(f"Error listing plans: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )
