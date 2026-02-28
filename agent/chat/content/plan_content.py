"""Plan content for Filmeto agent system."""
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType

if TYPE_CHECKING:
    from agent.plan.plan_models import Plan, PlanTask


# Status mapping from PlanTask status to QML-compatible status
_TASK_STATUS_MAP = {
    "created": "waiting",
    "ready": "waiting",
    "running": "running",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "cancelled",
}

# Plan status mapping
_PLAN_STATUS_MAP = {
    "created": "pending",
    "running": "in_progress",
    "paused": "pending",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "cancelled",
}


@dataclass
class PlanContent(StructureContent):
    """Plan content for task planning.

    Supports rendering plan information in chat messages with full task details
    and QML-compatible step format for UI rendering.
    """
    content_type: ContentType = ContentType.PLAN

    # Plan identification
    plan_id: str = ""
    project_name: str = ""

    # Plan metadata
    plan_title: Optional[str] = None
    plan_description: Optional[str] = None

    # Operation type: create, update, get, list, delete
    operation: str = "create"

    # Tasks in QML-compatible format: [{text, status}, ...]
    steps: List[Dict[str, Any]] = field(default_factory=list)

    # Rich task data for advanced rendering
    tasks: List[Dict[str, Any]] = field(default_factory=list)

    # Execution tracking
    current_step: int = 0
    total_steps: int = 0
    plan_status: str = "pending"  # pending, in_progress, completed, failed, cancelled

    # Statistics
    running_count: int = 0
    waiting_count: int = 0
    completed_count: int = 0
    failed_count: int = 0

    def _convert_tasks_to_steps(self) -> List[Dict[str, Any]]:
        """Convert rich tasks to QML-compatible steps format.

        Returns:
            List of steps in format: [{text: str, status: str, description: str, ...}, ...]
        """
        steps = []
        for task in self.tasks:
            task_status = task.get("status", "created")
            # Map task status to QML-compatible status
            qml_status = _TASK_STATUS_MAP.get(task_status, task_status)

            step = {
                "text": task.get("name", task.get("title", "Untitled Task")),
                "status": qml_status,
            }

            # Add optional fields for richer UI
            if task.get("id"):
                step["id"] = task.get("id")
            if task.get("description"):
                step["description"] = task.get("description")
            if task.get("title"):
                step["title"] = task.get("title")
            if task.get("needs"):
                step["needs"] = task.get("needs")
            if task.get("error_message"):
                step["error_message"] = task.get("error_message")

            steps.append(step)
        return steps

    def _get_data(self) -> Dict[str, Any]:
        """Get data dict for QML rendering.

        Returns QML-compatible format: {title, steps, ...}
        """
        # Use steps if already set, otherwise convert from tasks
        steps = self.steps if self.steps else self._convert_tasks_to_steps()

        data = {
            "plan_id": self.plan_id,
            "steps": steps,
            "current_step": self.current_step,
            "total_steps": self.total_steps or len(steps),
            "status": self.plan_status,
            "operation": self.operation,
        }

        # Add title if available
        if self.plan_title:
            data["title"] = self.plan_title

        # Add statistics
        if self.running_count or self.waiting_count or self.completed_count or self.failed_count:
            data["running_count"] = self.running_count
            data["waiting_count"] = self.waiting_count
            data["completed_count"] = self.completed_count
            data["failed_count"] = self.failed_count

        # Add rich tasks if available
        if self.tasks:
            data["tasks"] = self.tasks

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlanContent':
        """Create a PlanContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            plan_id=data_dict.get("plan_id", ""),
            project_name=data_dict.get("project_name", ""),
            plan_title=data_dict.get("title"),
            plan_description=data_dict.get("description"),
            operation=data_dict.get("operation", "create"),
            steps=data_dict.get("steps", []),
            tasks=data_dict.get("tasks", []),
            current_step=data_dict.get("current_step", 0),
            total_steps=data_dict.get("total_steps", 0),
            plan_status=data_dict.get("status", "pending"),
            running_count=data_dict.get("running_count", 0),
            waiting_count=data_dict.get("waiting_count", 0),
            completed_count=data_dict.get("completed_count", 0),
            failed_count=data_dict.get("failed_count", 0),
        )

    @classmethod
    def from_plan(
        cls,
        plan: 'Plan',
        operation: str = "create",
        **kwargs
    ) -> 'PlanContent':
        """Create a PlanContent from a Plan model.

        Args:
            plan: The Plan model object
            operation: Operation type (create, update, get, list, delete)
            **kwargs: Additional arguments to override defaults

        Returns:
            PlanContent instance with data from the Plan model
        """
        # Convert tasks to rich task format
        tasks = []
        running_count = 0
        waiting_count = 0
        completed_count = 0
        failed_count = 0

        for task in plan.tasks:
            task_dict = cls._convert_task_to_dict(task)
            tasks.append(task_dict)

            # Count by status
            status = task.status.value if hasattr(task.status, 'value') else str(task.status)
            if status in ("running",):
                running_count += 1
            elif status in ("created", "ready"):
                waiting_count += 1
            elif status in ("completed",):
                completed_count += 1
            elif status in ("failed", "cancelled"):
                failed_count += 1

        # Map plan status
        plan_status_value = plan.status.value if hasattr(plan.status, 'value') else str(plan.status)
        plan_status = _PLAN_STATUS_MAP.get(plan_status_value, plan_status_value)

        return cls(
            plan_id=plan.id,
            project_name=plan.project_name,
            plan_title=plan.name,
            plan_description=plan.description,
            operation=operation,
            tasks=tasks,
            total_steps=len(tasks),
            plan_status=plan_status,
            running_count=running_count,
            waiting_count=waiting_count,
            completed_count=completed_count,
            failed_count=failed_count,
            **kwargs
        )

    @staticmethod
    def _convert_task_to_dict(task: 'PlanTask') -> Dict[str, Any]:
        """Convert a PlanTask object to a dictionary."""
        return {
            'id': task.id,
            'name': task.name,
            'description': task.description,
            'title': task.title,
            'parameters': task.parameters,
            'needs': task.needs,
            'status': task.status.value if hasattr(task.status, 'value') else str(task.status),
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'error_message': task.error_message
        }


@dataclass
class StepContent(StructureContent):
    """Step content within a plan."""
    content_type: ContentType = ContentType.STEP
    step_id: str = ""
    step_number: int = 0
    description: str = ""
    step_status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None
    estimated_duration: Optional[int] = None  # in seconds

    def _get_data(self) -> Dict[str, Any]:
        data = {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "description": self.description,
            "status": self.step_status
        }
        if self.result is not None:
            data["result"] = self.result
        if self.error:
            data["error"] = self.error
        if self.estimated_duration is not None:
            data["estimated_duration"] = self.estimated_duration
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StepContent':
        """Create a StepContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            step_id=data_dict.get("step_id", ""),
            step_number=data_dict.get("step_number", 0),
            description=data_dict.get("description", ""),
            step_status=data_dict.get("status", "pending"),
            result=data_dict.get("result"),
            error=data_dict.get("error"),
            estimated_duration=data_dict.get("estimated_duration")
        )


@dataclass
class TaskListContent(StructureContent):
    """Task list content for tracking multiple tasks."""
    content_type: ContentType = ContentType.TASK_LIST
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    completed_count: int = 0
    total_count: int = 0
    list_title: Optional[str] = None

    def _get_data(self) -> Dict[str, Any]:
        data = {
            "tasks": self.tasks,
            "completed_count": self.completed_count,
            "total_count": self.total_count
        }
        if self.list_title:
            data["title"] = self.list_title
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskListContent':
        """Create a TaskListContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            tasks=data_dict.get("tasks", []),
            completed_count=data_dict.get("completed_count", 0),
            total_count=data_dict.get("total_count", 0),
            list_title=data_dict.get("title")
        )
