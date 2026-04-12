"""
Shot keyframe task executor with independent task queue.

Provides independent task execution for storyboard keyframe generation,
reusing existing Task module but without Timeline dependency.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

from blinker import signal

from app.data.task import Task, TaskResult, TaskProgress
from app.data.story_board.story_board_shot import StoryBoardShot
from utils.async_queue_utils import AsyncQueue

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.data.story_board.story_board_manager import StoryBoardManager
    from app.data.workspace import Workspace
    from app.spi.tool import BaseTool
    from .shot_task_manager import ShotTaskManager


class ShotTaskExecutor:
    """
    Independent task executor for shot keyframe generation.

    Features:
    - Independent task queue (create + execute)
    - Reuses Task, TaskResult, TaskProgress classes
    - Results written to shot.key_moment_image
    - Resources registered in project ResourceManager (Option B)
    - No Timeline dependency

    Signals (similar to ProjectTaskManager):
    - task_create: Emitted when a task is created
    - task_progress: Emitted during task execution
    - task_finished: Emitted when task completes
    """

    # Signals (matching ProjectTaskManager pattern)
    task_create = signal("shot_task_create")
    task_progress = signal("shot_task_progress")
    task_finished = signal("shot_task_finished")

    def __init__(
        self,
        story_board_manager: "StoryBoardManager",
        workspace: Optional["Workspace"] = None,
    ):
        """
        Initialize ShotTaskExecutor.

        Args:
            story_board_manager: StoryBoardManager for shot CRUD operations
            workspace: Workspace for accessing ResourceManager (required for Option B)
        """
        self.manager = story_board_manager
        self.workspace = workspace

        # Independent task queues (reuse AsyncQueue)
        self.create_queue = AsyncQueue()
        self.create_queue.connect("create", self._on_create_task)

        self.execute_queue = AsyncQueue()
        self.execute_queue.connect("execute", self._on_execute_task)

        # ShotTaskManager cache: key = "scene_id/shot_id"
        self._shot_task_managers: Dict[str, "ShotTaskManager"] = {}

    def set_workspace(self, workspace: "Workspace"):
        """Set workspace reference (e.g., after project load)."""
        self.workspace = workspace

    def get_shot_task_manager(
        self,
        shot: StoryBoardShot,
        shot_dir: str,
    ) -> "ShotTaskManager":
        """
        Get or create ShotTaskManager for a shot.

        Args:
            shot: StoryBoardShot instance
            shot_dir: Path to the shot directory

        Returns:
            ShotTaskManager instance
        """
        key = f"{shot.scene_id}/{shot.shot_id}"
        if key not in self._shot_task_managers:
            from .shot_task_manager import ShotTaskManager
            self._shot_task_managers[key] = ShotTaskManager(
                shot=shot,
                shot_dir=shot_dir,
                executor=self,
            )
        return self._shot_task_managers[key]

    def clear_shot_task_managers(self):
        """Clear cached ShotTaskManagers (e.g., on project switch)."""
        self._shot_task_managers.clear()

    # Signal connection methods (matching ProjectTaskManager API)
    def connect_task_create(self, func):
        """Connect to task creation signal."""
        self.task_create.connect(func)

    def connect_task_progress(self, func):
        """Connect to task progress signal."""
        self.task_progress.connect(func)

    def connect_task_finished(self, func):
        """Connect to task completion signal."""
        self.task_finished.connect(func)

    def submit_keyframe_task(
        self,
        shot: StoryBoardShot,
        shot_dir: str,
        prompt: str,
        tool: "BaseTool",
        options: Optional[Dict[str, Any]] = None,
    ):
        """
        Submit a keyframe generation task for a shot.

        Args:
            shot: Target StoryBoardShot
            shot_dir: Path to the shot directory
            prompt: Generation prompt
            tool: Tool instance (e.g., Text2Image)
            options: Additional options (width, height, etc.)
        """
        # Get ShotTaskManager for this shot
        shot_task_manager = self.get_shot_task_manager(shot, shot_dir)

        # Build task options
        task_options = {
            "tool": tool.get_tool_name(),
            "prompt": prompt,
            "shot_id": shot.shot_id,
            "scene_id": shot.scene_id,
            **(options or {}),
        }

        # Default dimensions
        task_options.setdefault("width", 1024)
        task_options.setdefault("height", 1024)

        # Attach manager and tool for async handler
        task_options["_shot_task_manager"] = shot_task_manager
        task_options["_tool_instance"] = tool

        # Add to create queue
        self.create_queue.add("create", task_options)
        logger.info(f"Submitted keyframe task for shot {shot.scene_id}/{shot.shot_id}")

    async def _on_create_task(self, options: Any):
        """
        Internal handler for task creation.

        Creates Task instance and adds to execute queue.
        """
        shot_task_manager = options.pop("_shot_task_manager", None)
        tool_instance = options.pop("_tool_instance", None)

        if not shot_task_manager:
            logger.warning("No ShotTaskManager in task options")
            return

        # Create Task through ShotTaskManager
        task = await shot_task_manager.create_task(options)

        if task:
            # Attach tool instance for execute handler
            task._tool_instance = tool_instance

            # Emit creation signal
            self.task_create.send(task)

            # Add to execute queue
            self.execute_queue.add("execute", task)

    async def _on_execute_task(self, task: Task):
        """
        Execute a shot keyframe task.

        Calls tool.execute() with the task.
        """
        tool_instance = getattr(task, "_tool_instance", None)
        if not tool_instance:
            logger.warning(f"Task {task.task_id} has no tool instance")
            return

        try:
            logger.info(f"Executing shot task {task.task_id} with tool {task.tool}")

            # Call tool.execute() - tool should handle shot tasks
            await tool_instance.execute(task)

        except Exception as e:
            logger.error(f"Shot task execution failed: {e}", exc_info=True)
            self._on_task_failed(task, str(e))

    def on_task_progress(self, task_progress: TaskProgress):
        """
        Handle task progress updates.

        Called by TaskProgress during execution.
        """
        self.task_progress.send(task_progress)

    def on_task_finished(self, result: TaskResult):
        """
        Handle task completion.

        Implements Option B:
        1. Register resources in project ResourceManager
        2. Persist result to shot.key_moment_image
        3. Emit finished signal

        This ordering ensures listeners see the updated keyframe when signal fires,
        and generated content is available in project resource library.
        """
        # Get shot info from task
        shot_id = result.task.options.get("shot_id")
        scene_id = result.task.options.get("scene_id")
        image_path = result.get_image_path()

        if not all([shot_id, scene_id, image_path]):
            logger.warning("Missing shot info or image path in task result")
            # Still emit signal so listeners know task finished (even if persist failed)
            self.task_finished.send(result)
            return

        # Step 1: Register resources in project ResourceManager (Option B)
        self._register_task_resources(result)

        # Step 2: Write to shot's key_moment_image BEFORE emitting signal
        try:
            success = self.manager.set_key_moment_image(
                scene_id=scene_id,
                shot_id=shot_id,
                image_path=image_path,
            )
            if success:
                logger.info(f"Keyframe saved for shot {scene_id}/{shot_id}: {image_path}")
            else:
                logger.warning(f"Failed to save keyframe for shot {scene_id}/{shot_id}")
        except Exception as e:
            logger.error(f"Error saving keyframe: {e}", exc_info=True)

        # Step 3: Emit finished signal AFTER persistence (listeners assume keyframe is available)
        self.task_finished.send(result)

    def _register_task_resources(self, result: TaskResult):
        """
        Register AI-generated outputs as project resources (Option B).

        Similar to Project._register_task_resources, but for shot tasks.
        """
        if not self.workspace:
            logger.warning("No workspace available for resource registration")
            return

        project = self.workspace.get_project()
        if not project:
            logger.warning("No project available for resource registration")
            return

        resource_manager = project.get_resource_manager()
        if not resource_manager:
            logger.warning("No resource_manager available for registration")
            return

        task = result.get_task()
        task_id = result.get_task_id()

        task_options = task.options
        tool = task_options.get("tool", "")
        model = task_options.get("model", "")
        prompt = task_options.get("prompt", "")
        shot_id = task_options.get("shot_id", "")
        scene_id = task_options.get("scene_id", "")

        # Additional metadata for shot keyframe
        additional_metadata = {
            "prompt": prompt,
            "model": model,
            "tool": tool,
            "task_id": task_id,
            "shot_id": shot_id,
            "scene_id": scene_id,
            "source": "shot_keyframe",  # Mark as shot-generated
        }

        # Register image output if exists
        image_path = result.get_image_path()
        if image_path and os.path.exists(image_path):
            try:
                resource = resource_manager.add_resource(
                    source_file_path=image_path,
                    source_type="ai_generated",
                    source_id=task_id,
                    additional_metadata=additional_metadata,
                )
                if resource:
                    logger.info(f"Registered shot keyframe resource: {resource.name}")
            except Exception as e:
                logger.error(f"Failed to register shot keyframe resource: {e}", exc_info=True)

        # Register video output if exists (for future video keyframes)
        video_path = result.get_video_path()
        if video_path and os.path.exists(video_path):
            try:
                resource = resource_manager.add_resource(
                    source_file_path=video_path,
                    source_type="ai_generated",
                    source_id=task_id,
                    additional_metadata=additional_metadata,
                )
                if resource:
                    logger.info(f"Registered shot video resource: {resource.name}")
            except Exception as e:
                logger.error(f"Failed to register shot video resource: {e}", exc_info=True)

    def _on_task_failed(self, task: Task, error: str):
        """Handle task failure."""
        logger.error(f"Shot task {task.task_id} failed: {error}")
        task.status = "failed"
        task.log = error

        # Save failed status to config
        try:
            from utils.yaml_utils import save_yaml
            save_yaml(task.config_path, {"status": "failed", "log": error, **task.options})
        except Exception:
            pass
