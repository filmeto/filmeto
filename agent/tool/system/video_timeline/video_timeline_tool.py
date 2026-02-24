"""VideoTimeline tool for managing video timeline items."""
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING, AsyncGenerator
import logging
import os

from ...base_tool import BaseTool, ToolMetadata, ToolParameter

# Tool directory for metadata loading
_tool_dir = Path(__file__).parent

if TYPE_CHECKING:
    from ....tool_context import ToolContext
    from agent.event.agent_event import AgentEvent


logger = logging.getLogger(__name__)


class VideoTimelineTool(BaseTool):
    """
    Tool for managing video timeline items in the Filmeto project.

    This tool provides CRUD operations for timeline items:
    - Add: Create a new timeline item
    - Delete: Remove a timeline item by index
    - Move: Move a timeline item to a different position
    - Update: Update the content (image/video) of a timeline item
    - Get: Retrieve information about timeline items

    Timeline indices are 1-indexed (first item is at index 1).
    """

    def __init__(self):
        super().__init__(
            name="video_timeline",
            description="Manage video timeline items - add, delete, move, and update timeline cards"
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
        Execute the video_timeline tool asynchronously.

        Args:
            parameters: Dictionary containing:
                - operation (str): Operation type (add, delete, move, update, get)
                - index (int, optional): Item index for delete, move, update
                - to_index (int, optional): Target index for move
                - image_path (str, optional): Image path for update
                - video_path (str, optional): Video path for update
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

            # Get timeline from context
            timeline = self._get_timeline(context)
            if timeline is None:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="Could not access timeline. Make sure you are in a valid project context."
                )
                return

            # Route to appropriate operation handler
            if operation == "add":
                async for event in self._handle_add(timeline, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "delete":
                async for event in self._handle_delete(timeline, parameters, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "move":
                async for event in self._handle_move(timeline, parameters, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "update":
                async for event in self._handle_update(timeline, parameters, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "list":
                async for event in self._handle_list_items(timeline, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "get":
                async for event in self._handle_get(timeline, parameters, project_name, react_type, run_id, step_id):
                    yield event
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Unknown operation: {operation}. Valid operations: add, delete, move, update, list, get"
                )

        except Exception as e:
            logger.error(f"Error in video_timeline tool: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    def _get_timeline(self, context: Optional["ToolContext"]) -> Optional['Timeline']:
        """Get the Timeline object from context."""
        if context is None:
            return None

        project = context.project
        if project is None:
            return None

        return project.get_timeline()

    async def _handle_add(
        self,
        timeline: 'Timeline',
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle add operation."""
        try:
            new_index = timeline.add_item()
            item_count = timeline.get_item_count()

            yield self._create_event(
                "tool_progress",
                project_name,
                react_type,
                run_id,
                step_id,
                result=f"Added new timeline item at index {new_index}"
            )

            yield self._create_event(
                "tool_end",
                project_name,
                react_type,
                run_id,
                step_id,
                ok=True,
                result={
                    "operation": "add",
                    "success": True,
                    "new_index": new_index,
                    "total_items": item_count,
                    "message": f"Successfully added new timeline item at index {new_index}. Total items: {item_count}"
                }
            )
        except Exception as e:
            logger.error(f"Error adding timeline item: {e}", exc_info=True)
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
        timeline: 'Timeline',
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle delete operation."""
        try:
            index = parameters.get("index")
            if index is None:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="index parameter is required for delete operation"
                )
                return

            index = int(index)
            success = timeline.delete_item(index)
            item_count = timeline.get_item_count()

            if success:
                yield self._create_event(
                    "tool_progress",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    result=f"Deleted timeline item at index {index}"
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
                        "deleted_index": index,
                        "total_items": item_count,
                        "message": f"Successfully deleted timeline item at index {index}. Total items: {item_count}"
                    }
                )
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Failed to delete timeline item at index {index}. Invalid index or item does not exist."
                )
        except ValueError:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error="index parameter must be a valid integer"
            )
        except Exception as e:
            logger.error(f"Error deleting timeline item: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    async def _handle_move(
        self,
        timeline: 'Timeline',
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle move operation."""
        try:
            index = parameters.get("index")
            to_index = parameters.get("to_index")

            if index is None or to_index is None:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="index and to_index parameters are required for move operation"
                )
                return

            index = int(index)
            to_index = int(to_index)
            success = timeline.move_item(index, to_index)

            if success:
                yield self._create_event(
                    "tool_progress",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    result=f"Moved timeline item from index {index} to {to_index}"
                )

                yield self._create_event(
                    "tool_end",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    ok=True,
                    result={
                        "operation": "move",
                        "success": True,
                        "from_index": index,
                        "to_index": to_index,
                        "message": f"Successfully moved timeline item from index {index} to {to_index}"
                    }
                )
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Failed to move timeline item. Invalid indices (from: {index}, to: {to_index}) or operation failed."
                )
        except ValueError:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error="index and to_index parameters must be valid integers"
            )
        except Exception as e:
            logger.error(f"Error moving timeline item: {e}", exc_info=True)
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
        timeline: 'Timeline',
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle update operation."""
        try:
            index = parameters.get("index")
            image_path = parameters.get("image_path")
            video_path = parameters.get("video_path")

            if index is None:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="index parameter is required for update operation"
                )
                return

            if image_path is None and video_path is None:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="At least one of image_path or video_path must be provided for update operation"
                )
                return

            index = int(index)

            # Validate file paths if provided
            if image_path and not os.path.exists(image_path):
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Image file not found: {image_path}"
                )
                return

            if video_path and not os.path.exists(video_path):
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Video file not found: {video_path}"
                )
                return

            success = timeline.update_item_content(index, image_path, video_path)

            if success:
                updated_parts = []
                if image_path:
                    updated_parts.append("image")
                if video_path:
                    updated_parts.append("video")

                yield self._create_event(
                    "tool_progress",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    result=f"Updated timeline item at index {index}: {', '.join(updated_parts)}"
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
                        "index": index,
                        "updated_image": image_path is not None,
                        "updated_video": video_path is not None,
                        "message": f"Successfully updated timeline item at index {index}"
                    }
                )
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Failed to update timeline item at index {index}. Invalid index or update failed."
                )
        except ValueError:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error="index parameter must be a valid integer"
            )
        except Exception as e:
            logger.error(f"Error updating timeline item: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    async def _handle_list_items(
        self,
        timeline: 'Timeline',
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle list_timeline_items operation - retrieve comprehensive timeline information."""
        try:
            timeline_info = timeline.list_items()

            # Create a summary message
            total_items = timeline_info["total_items"]
            total_duration = timeline_info["total_duration"]
            current_index = timeline_info["current_index"]

            summary_parts = []
            summary_parts.append(f"Timeline has {total_items} item(s)")
            summary_parts.append(f"Total duration: {total_duration:.2f} seconds")
            if current_index > 0:
                summary_parts.append(f"Currently selected: item #{current_index}")

            # Add item details summary
            if total_items > 0:
                items_with_video = sum(1 for item in timeline_info["items"] if item["has_video"])
                items_with_image_only = sum(1 for item in timeline_info["items"] if item["has_image"] and not item["has_video"])
                summary_parts.append(f"Items with video: {items_with_video}, image only: {items_with_image_only}")

            message = ". ".join(summary_parts)

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
                    "timeline": timeline_info,
                    "message": message
                }
            )
        except Exception as e:
            logger.error(f"Error getting timeline info: {e}", exc_info=True)
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
        timeline: 'Timeline',
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle get operation - retrieve a single timeline item by index."""
        try:
            index = parameters.get("index")
            if index is None:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="index parameter is required for get operation"
                )
                return

            index = int(index)

            if index < 1 or index > timeline.get_item_count():
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Invalid index {index}. Valid range: 1-{timeline.get_item_count()}"
                )
                return

            item = timeline.get_item(index)
            has_image = os.path.exists(item.image_path)
            has_video = os.path.exists(item.video_path)

            item_info = {
                "index": index,
                "has_image": has_image,
                "has_video": has_video,
                "duration": timeline.project.get_item_duration(index) if hasattr(timeline.project, 'get_item_duration') else None,
                "preview_path": item.get_preview_path(),
                "config": item.get_config(),
                "item_path": item.get_item_path(),
                "layers_path": item.get_layers_path(),
                "tasks_path": item.get_tasks_path(),
            }

            # Add prompt if available
            prompt = item.get_prompt()
            if prompt:
                item_info["prompt"] = prompt

            # Get layer count if layers exist
            if has_image or has_video:
                layer_manager = item.get_layer_manager()
                item_info["layer_count"] = len(layer_manager.layers) if layer_manager else 0

            # Create summary message
            content_type = "video" if has_video else "image" if has_image else "empty"
            message = f"Item #{index}: {content_type}"

            if item_info.get("duration"):
                message += f", duration: {item_info['duration']:.2f}s"

            if item_info.get("layer_count") is not None:
                message += f", layers: {item_info['layer_count']}"

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
                    "item": item_info,
                    "message": message
                }
            )
        except ValueError:
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error="index parameter must be a valid integer"
            )
        except Exception as e:
            logger.error(f"Error getting timeline item: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )
