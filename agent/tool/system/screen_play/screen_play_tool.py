"""ScreenPlay tool for managing screenplay scenes."""
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING, AsyncGenerator
import logging

from ...base_tool import BaseTool

# Tool directory for metadata loading
_tool_dir = Path(__file__).parent

if TYPE_CHECKING:
    from ....tool_context import ToolContext
    from agent.event.agent_event import AgentEvent
    from app.data.screen_play import ScreenPlayManager, ScreenPlayScene


logger = logging.getLogger(__name__)


class ScreenPlayTool(BaseTool):
    """
    Tool for managing screenplay scenes in the Filmeto project.

    This tool provides CRUD operations for screenplay scenes:
    - create: Create a new screenplay scene
    - get: Retrieve a scene by ID
    - update: Update an existing scene
    - delete: Delete a scene by ID
    - delete_all: Delete all scenes (dangerous operation)
    - delete_batch: Delete multiple scenes by IDs (dangerous operation)
    - list: List all scenes
    - get_by_title: Find a scene by title
    - get_by_character: Find scenes containing a character
    - get_by_location: Find scenes at a location
    """

    def __init__(self):
        super().__init__(
            name="screen_play",
            description="Manage screenplay scenes - create, read, update, delete, and query scenes"
        )
        # Set tool directory for metadata loading from tool.md
        self._tool_dir = _tool_dir

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
        Execute the screen_play tool asynchronously.

        Args:
            parameters: Dictionary containing:
                - operation (str): Operation type (create, get, update, delete, delete_all,
                                   delete_batch, list, get_by_title, get_by_character,
                                   get_by_location)
                - scene_id (str): Scene identifier for create, get, update, delete
                - scene_ids (list): List of scene identifiers for delete_batch
                - title (str): Scene title for create, update, get_by_title
                - content (str): Scene content for create, update
                - metadata (dict): Scene metadata for create, update
                - character_name (str): Character name for get_by_character
                - location (str): Location for get_by_location
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

            # Get ScreenPlayManager from context
            manager = self._get_screenplay_manager(context)
            if manager is None:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="Could not access screenplay manager. Make sure you are in a valid project context."
                )
                return

            # Route to appropriate operation handler
            if operation == "create":
                async for event in self._handle_create(manager, parameters, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "get":
                async for event in self._handle_get(manager, parameters, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "update":
                async for event in self._handle_update(manager, parameters, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "delete":
                async for event in self._handle_delete(manager, parameters, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "delete_all":
                async for event in self._handle_delete_all(manager, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "delete_batch":
                async for event in self._handle_delete_batch(manager, parameters, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "list":
                async for event in self._handle_list(manager, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "get_by_title":
                async for event in self._handle_get_by_title(manager, parameters, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "get_by_character":
                async for event in self._handle_get_by_character(manager, parameters, project_name, react_type, run_id, step_id):
                    yield event
            elif operation == "get_by_location":
                async for event in self._handle_get_by_location(manager, parameters, project_name, react_type, run_id, step_id):
                    yield event
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Unknown operation: {operation}. Valid operations: create, get, update, delete, delete_all, delete_batch, list, get_by_title, get_by_character, get_by_location"
                )

        except Exception as e:
            logger.error(f"Error in screen_play tool: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    def _get_screenplay_manager(self, context: Optional["ToolContext"]) -> Optional['ScreenPlayManager']:
        """Get the ScreenPlayManager object from context."""
        if context is None:
            return None

        # Use the get_screenplay_manager() method from ToolContext
        return context.get_screenplay_manager()

    async def _handle_create(
        self,
        manager: 'ScreenPlayManager',
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle create operation."""
        try:
            scene_id = parameters.get("scene_id")
            title = parameters.get("title", "")
            content = parameters.get("content", "")
            metadata = parameters.get("metadata", {})

            if not scene_id:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="scene_id parameter is required for create operation"
                )
                return

            success = manager.create_scene(scene_id, title, content, metadata)

            if success:
                yield self._create_event(
                    "tool_progress",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    result=f"Created screenplay scene: {scene_id}"
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
                        "scene_id": scene_id,
                        "message": f"Successfully created screenplay scene '{scene_id}'"
                    }
                )
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Failed to create screenplay scene '{scene_id}'"
                )
        except Exception as e:
            logger.error(f"Error creating screenplay scene: {e}", exc_info=True)
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
        manager: 'ScreenPlayManager',
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle get operation - retrieve a single scene by ID."""
        try:
            scene_id = parameters.get("scene_id")
            if not scene_id:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="scene_id parameter is required for get operation"
                )
                return

            scene = manager.get_scene(scene_id)

            if scene:
                scene_info = scene.to_dict()
                message = f"Scene '{scene_id}': {scene.title}"
                if scene.location:
                    message += f", Location: {scene.location}"
                if scene.characters:
                    message += f", Characters: {', '.join(scene.characters)}"

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
                        "scene": scene_info,
                        "message": message
                    }
                )
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Scene '{scene_id}' not found"
                )
        except Exception as e:
            logger.error(f"Error getting screenplay scene: {e}", exc_info=True)
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
        manager: 'ScreenPlayManager',
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle update operation."""
        try:
            scene_id = parameters.get("scene_id")
            title = parameters.get("title")
            content = parameters.get("content")
            metadata_updates = parameters.get("metadata")

            if not scene_id:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="scene_id parameter is required for update operation"
                )
                return

            if title is None and content is None and metadata_updates is None:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="At least one of title, content, or metadata must be provided for update operation"
                )
                return

            success = manager.update_scene(scene_id, title, content, metadata_updates)

            if success:
                updated_parts = []
                if title is not None:
                    updated_parts.append("title")
                if content is not None:
                    updated_parts.append("content")
                if metadata_updates is not None:
                    updated_parts.append("metadata")

                yield self._create_event(
                    "tool_progress",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    result=f"Updated screenplay scene '{scene_id}': {', '.join(updated_parts)}"
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
                        "scene_id": scene_id,
                        "updated_fields": updated_parts,
                        "message": f"Successfully updated screenplay scene '{scene_id}'"
                    }
                )
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Failed to update screenplay scene '{scene_id}'. Scene may not exist."
                )
        except Exception as e:
            logger.error(f"Error updating screenplay scene: {e}", exc_info=True)
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
        manager: 'ScreenPlayManager',
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle delete operation."""
        try:
            scene_id = parameters.get("scene_id")
            if not scene_id:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="scene_id parameter is required for delete operation"
                )
                return

            success = manager.delete_scene(scene_id)

            if success:
                yield self._create_event(
                    "tool_progress",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    result=f"Deleted screenplay scene: {scene_id}"
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
                        "scene_id": scene_id,
                        "message": f"Successfully deleted screenplay scene '{scene_id}'"
                    }
                )
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"Failed to delete screenplay scene '{scene_id}'. Scene may not exist."
                )
        except Exception as e:
            logger.error(f"Error deleting screenplay scene: {e}", exc_info=True)
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
        manager: 'ScreenPlayManager',
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle list operation - retrieve all scenes."""
        try:
            scenes = manager.list_scenes()

            scenes_info = []
            for scene in scenes:
                scene_info = {
                    "scene_id": scene.scene_id,
                    "title": scene.title,
                    "scene_number": scene.scene_number,
                    "location": scene.location,
                    "time_of_day": scene.time_of_day,
                    "characters": scene.characters,
                    "status": scene.status,
                    "page_count": scene.page_count,
                    "duration_minutes": scene.duration_minutes,
                }
                scenes_info.append(scene_info)

            # Create summary message
            total_scenes = len(scenes_info)
            message = f"Found {total_scenes} screenplay scene(s)"
            if total_scenes > 0:
                locations = set(s["location"] for s in scenes_info if s["location"])
                if locations:
                    message += f", Locations: {', '.join(sorted(locations))}"

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
                    "total_scenes": total_scenes,
                    "scenes": scenes_info,
                    "message": message
                }
            )
        except Exception as e:
            logger.error(f"Error listing screenplay scenes: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    async def _handle_get_by_title(
        self,
        manager: 'ScreenPlayManager',
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle get_by_title operation - find a scene by title."""
        try:
            title = parameters.get("title")
            if not title:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="title parameter is required for get_by_title operation"
                )
                return

            scene = manager.get_scene_by_title(title)

            if scene:
                scene_info = scene.to_dict()
                message = f"Found scene by title '{title}': {scene.scene_id}"

                yield self._create_event(
                    "tool_end",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    ok=True,
                    result={
                        "operation": "get_by_title",
                        "success": True,
                        "scene": scene_info,
                        "message": message
                    }
                )
            else:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error=f"No scene found with title '{title}'"
                )
        except Exception as e:
            logger.error(f"Error finding scene by title: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    async def _handle_get_by_character(
        self,
        manager: 'ScreenPlayManager',
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle get_by_character operation - find scenes containing a character."""
        try:
            character_name = parameters.get("character_name")
            if not character_name:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="character_name parameter is required for get_by_character operation"
                )
                return

            scenes = manager.get_scenes_by_character(character_name)

            scenes_info = []
            for scene in scenes:
                scene_info = {
                    "scene_id": scene.scene_id,
                    "title": scene.title,
                    "scene_number": scene.scene_number,
                    "location": scene.location,
                    "characters": scene.characters,
                }
                scenes_info.append(scene_info)

            total_scenes = len(scenes_info)
            message = f"Found {total_scenes} scene(s) with character '{character_name}'"

            yield self._create_event(
                "tool_end",
                project_name,
                react_type,
                run_id,
                step_id,
                ok=True,
                result={
                    "operation": "get_by_character",
                    "success": True,
                    "character_name": character_name,
                    "total_scenes": total_scenes,
                    "scenes": scenes_info,
                    "message": message
                }
            )
        except Exception as e:
            logger.error(f"Error finding scenes by character: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    async def _handle_get_by_location(
        self,
        manager: 'ScreenPlayManager',
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle get_by_location operation - find scenes at a location."""
        try:
            location = parameters.get("location")
            if not location:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="location parameter is required for get_by_location operation"
                )
                return

            scenes = manager.get_scenes_by_location(location)

            scenes_info = []
            for scene in scenes:
                scene_info = {
                    "scene_id": scene.scene_id,
                    "title": scene.title,
                    "scene_number": scene.scene_number,
                    "location": scene.location,
                    "characters": scene.characters,
                }
                scenes_info.append(scene_info)

            total_scenes = len(scenes_info)
            message = f"Found {total_scenes} scene(s) at location matching '{location}'"

            yield self._create_event(
                "tool_end",
                project_name,
                react_type,
                run_id,
                step_id,
                ok=True,
                result={
                    "operation": "get_by_location",
                    "success": True,
                    "location": location,
                    "total_scenes": total_scenes,
                    "scenes": scenes_info,
                    "message": message
                }
            )
        except Exception as e:
            logger.error(f"Error finding scenes by location: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    async def _handle_delete_all(
        self,
        manager: 'ScreenPlayManager',
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle delete_all operation - delete all screenplay scenes.

        WARNING: This is a destructive operation that permanently deletes all scenes.
        """
        try:
            result = manager.delete_all_scenes()
            deleted_count = result.get("deleted_count", 0)
            deleted_scene_ids = result.get("deleted_scene_ids", [])
            failed_scene_ids = result.get("failed_scene_ids", [])

            if deleted_count > 0:
                yield self._create_event(
                    "tool_progress",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    result=f"Deleted all screenplay scenes: {deleted_count} scenes removed"
                )

            message = f"Successfully deleted all {deleted_count} screenplay scenes."
            if failed_scene_ids:
                message = f"Deleted {deleted_count} scenes. Failed to delete: {', '.join(failed_scene_ids)}"
            elif deleted_count == 0:
                message = "No screenplay scenes found. Nothing to delete."

            yield self._create_event(
                "tool_end",
                project_name,
                react_type,
                run_id,
                step_id,
                ok=True,
                result={
                    "operation": "delete_all",
                    "success": True,
                    "deleted_count": deleted_count,
                    "deleted_scene_ids": deleted_scene_ids,
                    "failed_scene_ids": failed_scene_ids,
                    "message": message
                }
            )
        except Exception as e:
            logger.error(f"Error deleting all screenplay scenes: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )

    async def _handle_delete_batch(
        self,
        manager: 'ScreenPlayManager',
        parameters: Dict[str, Any],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle delete_batch operation - delete multiple scenes by IDs.

        WARNING: This is a destructive operation that permanently deletes scenes.
        """
        try:
            scene_ids = parameters.get("scene_ids")
            if not scene_ids:
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="scene_ids parameter is required for delete_batch operation"
                )
                return

            if not isinstance(scene_ids, list):
                yield self._create_event(
                    "error",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    error="scene_ids must be a list of scene identifiers"
                )
                return

            result = manager.delete_scenes(scene_ids)
            deleted_count = result.get("deleted_count", 0)
            deleted_scene_ids = result.get("deleted_scene_ids", [])
            not_found_ids = result.get("not_found_ids", [])
            failed_scene_ids = result.get("failed_scene_ids", [])

            if deleted_count > 0:
                yield self._create_event(
                    "tool_progress",
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                    result=f"Deleted {deleted_count} screenplay scenes"
                )

            message = f"Successfully deleted {deleted_count} screenplay scenes."
            if not_found_ids:
                message += f" Not found: {', '.join(not_found_ids)}."
            if failed_scene_ids:
                message += f" Failed: {', '.join(failed_scene_ids)}."
            if deleted_count == 0:
                message = "None of the specified scenes were found. Nothing to delete."

            yield self._create_event(
                "tool_end",
                project_name,
                react_type,
                run_id,
                step_id,
                ok=True,
                result={
                    "operation": "delete_batch",
                    "success": True,
                    "deleted_count": deleted_count,
                    "deleted_scene_ids": deleted_scene_ids,
                    "not_found_ids": not_found_ids,
                    "failed_scene_ids": failed_scene_ids,
                    "message": message
                }
            )
        except Exception as e:
            logger.error(f"Error deleting batch screenplay scenes: {e}", exc_info=True)
            yield self._create_event(
                "error",
                project_name,
                react_type,
                run_id,
                step_id,
                error=str(e)
            )
