"""
Shot-level task manager for keyframe generation.

Similar to TimelineItemTaskManager but stores tasks in Shot directory,
independent of Timeline.
"""

from __future__ import annotations

import os
import asyncio
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from app.data.task import Task
from utils.yaml_utils import save_yaml_async, load_yaml_async, path_exists, to_thread

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.data.story_board.story_board_shot import StoryBoardShot
    from .shot_task_executor import ShotTaskExecutor


class ShotTaskManager:
    """
    Shot-level task manager for keyframe generation.

    Tasks are stored in: shot_dir/keyframes/{task_id}/config.yml

    Similar to TimelineItemTaskManager but independent of Timeline.
    """

    def __init__(
        self,
        shot: "StoryBoardShot",
        shot_dir: str,
        executor: "ShotTaskExecutor",
    ):
        """
        Initialize ShotTaskManager.

        Args:
            shot: The StoryBoardShot instance
            shot_dir: Path to the shot directory (shot_dir/keyframes will be used)
            executor: ShotTaskExecutor for progress callbacks
        """
        self.shot = shot
        self.shot_dir = shot_dir
        self.executor = executor

        # Task storage path: shot_dir/keyframes/
        self.tasks_path = os.path.join(shot_dir, "keyframes")
        self.tasks: Dict[str, Task] = {}

        # Task index file for tracking next task number
        self._index_path = os.path.join(self.tasks_path, "_index.yml")

        # Create tasks directory
        os.makedirs(self.tasks_path, exist_ok=True)

    def _get_next_task_index(self) -> int:
        """Get the next task index for this shot."""
        if os.path.exists(self._index_path):
            try:
                import yaml
                with open(self._index_path, "r") as f:
                    data = yaml.safe_load(f) or {}
                return data.get("next_index", 0)
            except Exception:
                return 0
        return 0

    def _increment_task_index(self):
        """Increment the task index."""
        current = self._get_next_task_index() + 1
        try:
            import yaml
            os.makedirs(os.path.dirname(self._index_path), exist_ok=True)
            with open(self._index_path, "w") as f:
                yaml.safe_dump({"next_index": current}, f)
        except Exception as e:
            logger.warning(f"Failed to save task index: {e}")

    async def create_task(self, options: Any) -> Optional[Task]:
        """
        Create a new task for this shot.

        Args:
            options: Task configuration containing:
                - tool: Tool name (e.g., "text2image")
                - prompt: Generation prompt
                - width/height: Image dimensions
                - shot_id, scene_id: Shot identifiers (added automatically)

        Returns:
            Task instance or None if creation failed
        """
        try:
            num = self._get_next_task_index()
            self._increment_task_index()

            # Task directory: shot_dir/keyframes/{num}/
            task_fold_path = os.path.join(self.tasks_path, str(num))
            os.makedirs(task_fold_path, exist_ok=True)

            # Add shot context to options
            options["shot_id"] = self.shot.shot_id
            options["scene_id"] = self.shot.scene_id
            options["shot_path"] = self.shot_dir
            options["is_shot_task"] = True

            # Save config
            config_path = os.path.join(task_fold_path, "config.yml")
            await save_yaml_async(config_path, options)

            # Create Task instance (reuse existing Task class)
            # Pass executor as progress_callback_manager for progress callbacks
            task = Task(
                task_storage_manager=self,
                progress_callback_manager=self.executor,
                path=task_fold_path,
                options=options,
            )

            self.tasks[str(num)] = task
            logger.info(f"Created shot task {num} for {self.shot.scene_id}/{self.shot.shot_id}")

            return task

        except Exception as e:
            logger.error(f"Failed to create shot task: {e}", exc_info=True)
            return None

    def _collect_numeric_task_dirs(self) -> List[str]:
        """Collect numeric task directory names."""
        if not os.path.exists(self.tasks_path):
            return []
        names: List[str] = []
        for d in os.listdir(self.tasks_path):
            dir_path = os.path.join(self.tasks_path, d)
            if os.path.isdir(dir_path) and d.isdigit():
                names.append(d)
        return names

    async def load_all_tasks_async(self, *, apply: bool = True) -> List[Task]:
        """
        Load all tasks asynchronously.

        Args:
            apply: If True, update self.tasks dict; if False, just return list

        Returns:
            List of Task instances
        """
        if not await path_exists(self.tasks_path):
            return []

        try:
            task_dir_names = await to_thread(self._collect_numeric_task_dirs)
            if apply:
                self.tasks.clear()

            async def load_one(task_dir_name: str) -> tuple:
                task_dir_path = os.path.join(self.tasks_path, task_dir_name)
                config_path = os.path.join(task_dir_path, "config.yml")
                options: Dict[str, Any] = {}
                if await path_exists(config_path):
                    try:
                        options = await load_yaml_async(config_path) or {}
                    except Exception as e:
                        logger.warning(f"Failed to load task config {config_path}: {e}")
                        options = {}
                return task_dir_name, Task(
                    self, self.executor, task_dir_path, options
                )

            pairs = await asyncio.gather(*(load_one(d) for d in task_dir_names))
            loaded_tasks: List[Task] = []
            for name, task in pairs:
                if apply:
                    self.tasks[name] = task
                loaded_tasks.append(task)

            logger.info(f"Loaded {len(loaded_tasks)} shot tasks for {self.shot.scene_id}/{self.shot.shot_id}")
            return loaded_tasks

        except Exception as e:
            logger.error(f"Failed to load shot tasks: {e}", exc_info=True)
            return []

    def load_all_tasks(self) -> List[Task]:
        """Load all tasks synchronously."""
        from utils.yaml_utils import run_coroutine_blocking
        try:
            return run_coroutine_blocking(self.load_all_tasks_async(apply=True))
        except Exception as e:
            logger.error(f"Failed to load shot tasks: {e}", exc_info=True)
            return []

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        if not self.tasks:
            self.load_all_tasks()
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        """Get all tasks for this shot."""
        if not self.tasks:
            self.load_all_tasks()
        return list(self.tasks.values())

    def get_shot_id(self) -> str:
        """Get the shot ID this manager belongs to."""
        return self.shot.shot_id

    def get_scene_id(self) -> str:
        """Get the scene ID this manager belongs to."""
        return self.shot.scene_id
