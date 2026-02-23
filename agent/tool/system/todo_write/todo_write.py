"""TodoWrite tool for managing TODO lists in React process."""
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING, AsyncGenerator
from datetime import datetime
import logging

from ...base_tool import BaseTool, ToolMetadata, ToolParameter

# Tool directory for metadata loading
_tool_dir = Path(__file__).parent

if TYPE_CHECKING:
    from ....tool_context import ToolContext
    from agent.event.agent_event import AgentEvent


logger = logging.getLogger(__name__)


class TodoWriteTool(BaseTool):
    """
    Tool for creating and managing structured task lists during the React process.

    This tool helps the AI assistant track progress and organize complex tasks,
    providing clear visibility into the work being performed.

    The tool should be used for:
    - Complex tasks requiring multiple steps
    - Feature implementation involving multiple components
    - Refactoring operations across multiple files
    - Work involving three or more different operations

    For simple single-step tasks or pure information queries, this tool should not be used.

    Usage:
    - First call creates the initial TODO list with all items
    - Subsequent calls update the status of existing items
    - TODO state is persisted in the React checkpoint for recovery
    - Each React loop has its own isolated TODO state
    """

    def __init__(self):
        super().__init__(
            name="todo_write",
            description="Create and manage structured task lists for tracking progress during complex tasks"
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
        Execute the todo_write tool asynchronously.

        This method updates the TODO state in the React instance through the ToolContext.
        The React instance is responsible for storing the TODO state in checkpoints.

        Args:
            parameters: Dictionary containing:
                - todos: List of TODO items, each with:
                    - content (str): Task description
                    - status (str): Task status (pending, in_progress, completed)
                    - activeForm (str): Present continuous form of the action
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
        try:
            todos = parameters.get("todos")
            if not todos:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="todos parameter is required and must be a non-empty array"
                )
                return

            if not isinstance(todos, list):
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="todos parameter must be an array"
                )
                return

            # Get the React instance from the context to update its todo_state
            # The React instance is passed through context._data['_react_instance']
            if context:
                react_instance = context.get('_react_instance')
                if react_instance:
                    result = self._update_react_todo_state(react_instance, todos)
                    yield self._create_event(
                        "tool_progress",
                        project_name,
                        react_type,
                        run_id,
                        step_id,
                        result="TODO list updated"
                    )
                    yield self._create_event(
                        "tool_end",
                        project_name,
                        react_type,
                        run_id,
                        step_id,
                        ok=True,
                        result=result
                    )
                    return

            # If no React instance available, just return the parsed todos
            # This allows the tool to work in isolation for testing
            parsed_items = []
            for todo in todos:
                item = self._parse_todo_item(todo)
                if item:
                    parsed_items.append(item)

            yield self._create_event(
                "tool_end",
                project_name,
                react_type,
                run_id,
                step_id,
                ok=True,
                result={
                    "message": "TODO list updated",
                    "count": len(parsed_items),
                    "items": [item.to_dict() for item in parsed_items]
                }
            )
        except Exception as e:
            logger.error(f"Error in todo_write tool: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    def _update_react_todo_state(self, react_instance, todos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update the React instance's TODO state."""
        from ....react.types import TodoState

        existing_ids = {item.id for item in react_instance.todo_state.items}
        new_items = list(react_instance.todo_state.items)
        updated_count = 0
        created_count = 0

        for todo in todos:
            item = self._parse_todo_item(todo, existing_ids)
            if not item:
                continue

            # Check if this is an update to an existing item
            found = False
            for i, existing_item in enumerate(new_items):
                if existing_item.id == item.id or existing_item.title == item.title:
                    # Update existing item
                    new_items[i] = item
                    updated_count += 1
                    found = True
                    break

            if not found:
                # Add new item
                new_items.append(item)
                created_count += 1

        # Create new TodoState
        new_state = TodoState(
            items=new_items,
            version=react_instance.todo_state.version + 1
        )

        # Update React's todo_state
        react_instance.todo_state = new_state

        # Create a TODO update event that React can emit
        # Store it in a special attribute that React's tool execution loop can check
        if hasattr(react_instance, '_pending_todo_update'):
            react_instance._pending_todo_update = {
                "todo_state": new_state.to_dict(),
            }
        else:
            # React class might not have this attribute yet, so we'll skip event emission
            # The TODO state is still updated and will be checkpointed
            pass

        # Emit TODO update event
        summary = new_state.get_summary()
        logger.debug(f"TODO state updated: {created_count} created, {updated_count} updated")

        return {
            "message": "TODO list updated successfully",
            "created": created_count,
            "updated": updated_count,
            "total": summary["total"],
            "pending": summary["pending"],
            "in_progress": summary["in_progress"],
            "completed": summary["completed"],
            "version": new_state.version
        }

    def _parse_todo_item(self, todo: Dict[str, Any], existing_ids: Optional[set] = None) -> Optional[Any]:
        """Parse a TODO item from the input format.

        Args:
            todo: Dict containing content, status, and activeForm
            existing_ids: Set of existing TODO item IDs (for deduplication)

        Returns:
            TodoItem or None if parsing fails
        """
        from ....react.types import TodoItem, TodoStatus

        if not isinstance(todo, dict):
            return None

        content = todo.get("content") or todo.get("title", "")
        status_str = todo.get("status", "pending")
        active_form = todo.get("activeForm", "")

        if not content:
            return None

        # Map status string to TodoStatus enum
        status_map = {
            "pending": TodoStatus.PENDING,
            "in_progress": TodoStatus.IN_PROGRESS,
            "completed": TodoStatus.COMPLETED,
            "failed": TodoStatus.FAILED,
            "blocked": TodoStatus.BLOCKED,
        }
        status = status_map.get(status_str, TodoStatus.PENDING)

        # Use activeForm as the title if available, otherwise use content
        title = active_form if active_form else content

        # Generate a unique ID based on the title (for deduplication)
        import hashlib
        id_hash = hashlib.md5(title.encode()).hexdigest()[:8]
        item_id = f"todo_{id_hash}"

        # Create TodoItem
        return TodoItem(
            id=item_id,
            title=title,
            description=content,
            status=status,
            priority=3,
            dependencies=[],
            metadata={"activeForm": active_form},
            created_at=datetime.now().timestamp(),
            updated_at=datetime.now().timestamp(),
        )
