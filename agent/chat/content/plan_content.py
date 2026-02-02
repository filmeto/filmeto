"""Plan content for Filmeto agent system."""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


@dataclass
class PlanContent(StructureContent):
    """Plan content for task planning."""
    content_type: ContentType = ContentType.PLAN
    plan_id: str = ""
    plan_title: Optional[str] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    total_steps: int = 0
    plan_status: str = "pending"  # pending, in_progress, completed, failed

    def _get_data(self) -> Dict[str, Any]:
        data = {
            "plan_id": self.plan_id,
            "steps": self.steps,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "status": self.plan_status
        }
        if self.plan_title:
            data["title"] = self.plan_title
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
            plan_title=data_dict.get("title"),
            steps=data_dict.get("steps", []),
            current_step=data_dict.get("current_step", 0),
            total_steps=data_dict.get("total_steps", 0),
            plan_status=data_dict.get("status", "pending")
        )


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
