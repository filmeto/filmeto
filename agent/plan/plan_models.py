from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid


class PlanStatus(Enum):
    """Enumeration of possible statuses for a Plan"""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(Enum):
    """Enumeration of possible statuses for a PlanTask"""
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PlanTask:
    """
    Represents a single task in a Plan.

    A task defines what needs to be done, which member title should do it,
    and what dependencies it has on other tasks.
    """
    id: str
    name: str
    description: str
    title: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    needs: List[str] = field(default_factory=list)  # List of task IDs this task depends on
    status: TaskStatus = TaskStatus.CREATED
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class Plan:
    """
    Represents a plan definition.

    This contains the task definitions and their dependencies but not execution state.
    """
    id: str
    project_name: str  # Stores the project name as identifier
    name: str
    description: str
    tasks: List[PlanTask] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    status: PlanStatus = PlanStatus.CREATED
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanInstance:
    """
    Represents an instance of a Plan with execution state.

    This tracks the actual execution of a plan, including task statuses.
    """
    plan_id: str
    instance_id: str
    project_name: str  # Stores the project name as identifier
    tasks: List[PlanTask] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: PlanStatus = PlanStatus.CREATED
    metadata: Dict[str, Any] = field(default_factory=dict)