"""Todo tool for managing TODO lists in React process."""
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING, AsyncGenerator
from datetime import datetime
import logging
import hashlib

from ...base_tool import BaseTool, ToolMetadata, ToolParameter

# Tool directory for metadata loading
_tool_dir = Path(__file__).parent

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ....tool_context import ToolContext
    from agent.event.agent_event import AgentEvent


class TodoTool(BaseTool):
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

    Supported operations:
    - create: Create new TODO items or replace the entire TODO list
    - delete: Delete specific TODO items by ID or title
    - update: Update specific TODO items (status, content, etc.)
    - get: Get specific TODO item or the entire TODO list
    - list: List all TODO items with their current status

    TODO state is persisted in the React checkpoint for recovery.
    Each React loop has its own isolated TODO state.
    """

    def __init__(self):
        super().__init__(
            name="todo",
            description="Manage TODO lists for tracking progress during complex tasks - create, delete, update, get, and list items"
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
        Execute the todo tool asynchronously.

        This method updates the TODO state in the React instance through the ToolContext.
        The React instance is responsible for storing the TODO state in checkpoints.

        Args:
            parameters: Dictionary containing:
                - operation (str): Operation type (create, delete, update, get, list)
                - todos (list, optional): List of TODO items for create operation
                - todo_id (str, optional): TODO item ID for delete, update, get operations
                - title (str, optional): TODO title for delete, update, get operations
                - content (str, optional): New content for update operation
                - status (str, optional): New status for update operation
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
            operation = parameters.get("operation", "create")

            # Route to appropriate operation handler
            if operation == "create":
                async for event in self._handle_create(
                    parameters, context, project_name, react_type, run_id, step_id
                ):
                    yield event
            elif operation == "delete":
                async for event in self._handle_delete(
                    parameters, context, project_name, react_type, run_id, step_id
                ):
                    yield event
            elif operation == "update":
                async for event in self._handle_update(
                    parameters, context, project_name, react_type, run_id, step_id
                ):
                    yield event
            elif operation == "get":
                async for event in self._handle_get(
                    parameters, context, project_name, react_type, run_id, step_id
                ):
                    yield event
            elif operation == "list":
                async for event in self._handle_list(
                    parameters, context, project_name, react_type, run_id, step_id
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
            logger.error(f"Error in todo tool: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    def _get_react_instance(self, context: Optional["ToolContext"]) -> Optional[Any]:
        """Get the React instance from the context."""
        if context:
            return context.get('_react_instance')
        return None

    def _get_todo_state(self, react_instance) -> Optional[Any]:
        """Get the current TODO state from React instance."""
        if react_instance and hasattr(react_instance, 'todo_state'):
            return react_instance.todo_state
        return None

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
        todo_id = todo.get("id")

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

        # Generate or use provided ID
        if todo_id:
            item_id = todo_id
        else:
            # Generate a unique ID based on the title (for deduplication)
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

    def _update_react_todo_state(self, react_instance, new_items: list) -> Dict[str, Any]:
        """Update the React instance's TODO state."""
        from ....react.types import TodoState

        new_state = TodoState(
            items=new_items,
            version=react_instance.todo_state.version + 1
        )

        # Update React's todo_state
        react_instance.todo_state = new_state

        # Create a TODO update event that React can emit
        if hasattr(react_instance, '_pending_todo_update'):
            react_instance._pending_todo_update = {
                "todo_state": new_state.to_dict(),
            }

        # Emit TODO update event
        summary = new_state.get_summary()
        logger.debug(f"TODO state updated: {summary}")

        return {
            "message": "TODO list updated successfully",
            "total": summary["total"],
            "pending": summary["pending"],
            "in_progress": summary["in_progress"],
            "completed": summary["completed"],
            "version": new_state.version
        }

    def _todo_item_to_dict(self, item) -> Dict[str, Any]:
        """Convert a TodoItem to a dictionary."""
        from ....react.types import TodoStatus

        status_map = {
            TodoStatus.PENDING: "pending",
            TodoStatus.IN_PROGRESS: "in_progress",
            TodoStatus.COMPLETED: "completed",
            TodoStatus.FAILED: "failed",
            TodoStatus.BLOCKED: "blocked",
        }

        return {
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "status": status_map.get(item.status, "pending"),
            "activeForm": item.metadata.get("activeForm", "") if item.metadata else "",
            "priority": item.priority,
            "dependencies": item.dependencies,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    async def _handle_create(
        self,
        parameters: Dict[str, Any],
        context: Optional["ToolContext"],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle create operation - create new TODO items or replace the list."""
        try:
            todos = parameters.get("todos")
            if not todos:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="todos parameter is required for create operation"
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

            # Get the React instance from the context
            react_instance = self._get_react_instance(context)

            parsed_items = []
            for todo in todos:
                item = self._parse_todo_item(todo)
                if item:
                    parsed_items.append(item)

            if react_instance:
                existing_ids = {item.id for item in react_instance.todo_state.items}
                new_items = list(react_instance.todo_state.items)
                updated_count = 0
                created_count = 0

                for item in parsed_items:
                    # Check if this is an update to an existing item
                    found = False
                    for i, existing_item in enumerate(new_items):
                        if existing_item.id == item.id or existing_item.title == item.title:
                            new_items[i] = item
                            updated_count += 1
                            found = True
                            break

                    if not found:
                        new_items.append(item)
                        created_count += 1

                result = self._update_react_todo_state(react_instance, new_items)

                yield self._create_event(
                    "tool_progress",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    result=f"Created {created_count} new TODO items, updated {updated_count} items"
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
                        **result,
                        "items": [self._todo_item_to_dict(item) for item in new_items]
                    }
                )
            else:
                # No React instance available, just return parsed todos
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
                        "message": "TODO list created",
                        "count": len(parsed_items),
                        "items": [self._todo_item_to_dict(item) for item in parsed_items]
                    }
                )
        except Exception as e:
            logger.error(f"Error creating TODO items: {e}", exc_info=True)
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
        parameters: Dict[str, Any],
        context: Optional["ToolContext"],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle delete operation - delete specific TODO items."""
        try:
            react_instance = self._get_react_instance(context)
            if not react_instance:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="No React instance available for delete operation"
                )
                return

            todo_id = parameters.get("todo_id")
            title = parameters.get("title")

            if not todo_id and not title:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="Either todo_id or title parameter is required for delete operation"
                )
                return

            current_items = list(react_instance.todo_state.items)
            original_count = len(current_items)

            # Filter out items to delete
            new_items = [
                item for item in current_items
                if item.id != todo_id and item.title != title
            ]

            deleted_count = original_count - len(new_items)

            if deleted_count == 0:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"No TODO item found with id='{todo_id}' or title='{title}'"
                )
                return

            result = self._update_react_todo_state(react_instance, new_items)

            yield self._create_event(
                "tool_progress",
                project_name,
                react_type,
                run_id,
                step_id,
                result=f"Deleted {deleted_count} TODO item(s)"
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
                    "deleted_count": deleted_count,
                    **result,
                    "items": [self._todo_item_to_dict(item) for item in new_items]
                }
            )
        except Exception as e:
            logger.error(f"Error deleting TODO items: {e}", exc_info=True)
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
        parameters: Dict[str, Any],
        context: Optional["ToolContext"],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle update operation - update specific TODO items."""
        try:
            react_instance = self._get_react_instance(context)
            if not react_instance:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="No React instance available for update operation"
                )
                return

            todo_id = parameters.get("todo_id")
            title = parameters.get("title")
            content = parameters.get("content")
            status_str = parameters.get("status")
            active_form = parameters.get("activeForm")

            if not todo_id and not title:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="Either todo_id or title parameter is required for update operation"
                )
                return

            current_items = list(react_instance.todo_state.items)
            updated_count = 0

            for item in current_items:
                if item.id == todo_id or item.title == title:
                    from ....react.types import TodoStatus

                    # Update fields if provided
                    if content is not None:
                        item.description = content
                    if active_form is not None:
                        item.title = active_form
                        item.metadata = item.metadata or {}
                        item.metadata["activeForm"] = active_form
                    if status_str is not None:
                        status_map = {
                            "pending": TodoStatus.PENDING,
                            "in_progress": TodoStatus.IN_PROGRESS,
                            "completed": TodoStatus.COMPLETED,
                            "failed": TodoStatus.FAILED,
                            "blocked": TodoStatus.BLOCKED,
                        }
                        item.status = status_map.get(status_str, item.status)

                    item.updated_at = datetime.now().timestamp()
                    updated_count += 1

            if updated_count == 0:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"No TODO item found with id='{todo_id}' or title='{title}'"
                )
                return

            result = self._update_react_todo_state(react_instance, current_items)

            yield self._create_event(
                "tool_progress",
                project_name,
                react_type,
                run_id,
                step_id,
                result=f"Updated {updated_count} TODO item(s)"
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
                    "updated_count": updated_count,
                    **result,
                    "items": [self._todo_item_to_dict(item) for item in current_items]
                }
            )
        except Exception as e:
            logger.error(f"Error updating TODO items: {e}", exc_info=True)
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
        parameters: Dict[str, Any],
        context: Optional["ToolContext"],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle get operation - get specific TODO item or the entire list."""
        try:
            react_instance = self._get_react_instance(context)
            if not react_instance:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="No React instance available for get operation"
                )
                return

            todo_id = parameters.get("todo_id")
            title = parameters.get("title")

            current_items = list(react_instance.todo_state.items)

            if not todo_id and not title:
                # Get all items (same as list)
                items_dict = [self._todo_item_to_dict(item) for item in current_items]
                summary = react_instance.todo_state.get_summary()

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
                        "items": items_dict,
                        **summary
                    }
                )
                return

            # Find specific item
            found_item = None
            for item in current_items:
                if item.id == todo_id or item.title == title:
                    found_item = self._todo_item_to_dict(item)
                    break

            if found_item:
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
                        "item": found_item
                    }
                )
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"No TODO item found with id='{todo_id}' or title='{title}'"
                )
        except Exception as e:
            logger.error(f"Error getting TODO items: {e}", exc_info=True)
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
        parameters: Dict[str, Any],
        context: Optional["ToolContext"],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle list operation - list all TODO items."""
        try:
            react_instance = self._get_react_instance(context)

            if react_instance:
                current_items = list(react_instance.todo_state.items)
                summary = react_instance.todo_state.get_summary()
            else:
                # No React instance, return empty list
                current_items = []
                summary = {"total": 0, "pending": 0, "in_progress": 0, "completed": 0}

            items_dict = [self._todo_item_to_dict(item) for item in current_items]

            message = f"Found {summary['total']} TODO item(s)"

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
                    "items": items_dict,
                    **summary,
                    "message": message
                }
            )
        except Exception as e:
            logger.error(f"Error listing TODO items: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )
