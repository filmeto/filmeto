"""TodoWrite content for displaying and updating TODO lists."""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


@dataclass
class TodoWriteContent(StructureContent):
    """Content for displaying and incrementally updating TODO lists."""

    content_type: ContentType = ContentType.TODO_WRITE

    # TODO items list
    todos: List[Dict[str, Any]] = None

    # Summary statistics
    total: int = 0
    pending: int = 0
    in_progress: int = 0
    completed: int = 0
    failed: int = 0
    blocked: int = 0

    # Version for tracking updates
    version: int = 0

    def __post_init__(self):
        if self.todos is None:
            self.todos = []

    def _get_data(self) -> Dict[str, Any]:
        return {
            "todos": self.todos,
            "total": self.total,
            "pending": self.pending,
            "in_progress": self.in_progress,
            "completed": self.completed,
            "failed": self.failed,
            "blocked": self.blocked,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TodoWriteContent':
        """Create a TodoWriteContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            todos=data_dict.get("todos", []),
            total=data_dict.get("total", 0),
            pending=data_dict.get("pending", 0),
            in_progress=data_dict.get("in_progress", 0),
            completed=data_dict.get("completed", 0),
            failed=data_dict.get("failed", 0),
            blocked=data_dict.get("blocked", 0),
            version=data_dict.get("version", 0),
        )

    @classmethod
    def from_todo_state(cls, todo_state, title: str = "TODO List",
                        description: str = "Task progress tracking") -> 'TodoWriteContent':
        """Create TodoWriteContent from TodoState."""
        summary = todo_state.get_summary()
        return cls(
            title=title,
            description=description,
            todos=[item.to_dict() for item in todo_state.items],
            total=summary["total"],
            pending=summary["pending"],
            in_progress=summary["in_progress"],
            completed=summary["completed"],
            failed=summary["failed"],
            blocked=summary["blocked"],
            version=todo_state.version,
        )

    def update_todos(self, todos: List[Dict[str, Any]], **kwargs):
        """Incrementally update TODO list and statistics."""
        self.todos = todos
        self.total = len(todos)
        self.pending = sum(1 for t in todos if t.get("status") == "pending")
        self.in_progress = sum(1 for t in todos if t.get("status") == "in_progress")
        self.completed = sum(1 for t in todos if t.get("status") == "completed")
        self.failed = sum(1 for t in todos if t.get("status") == "failed")
        self.blocked = sum(1 for t in todos if t.get("status") == "blocked")
        if "version" in kwargs:
            self.version = kwargs["version"]
        self.status = ContentStatus.UPDATING
