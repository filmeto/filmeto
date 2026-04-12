"""
Task Management Module

This module provides a two-tier task management architecture:

1. ProjectTaskManager: Project-level task orchestration
   - Manages task signals (create, progress, finished)
   - Handles task execution queue
   - Coordinates task submission across timeline items

2. TimelineItemTaskManager: Timeline-item-level task storage
   - Manages task storage for a specific timeline item
   - Handles task CRUD operations
   - Provides task listing and pagination
"""

import asyncio
import os
import logging
from typing import Any, Optional, Dict, List, Union, TYPE_CHECKING

from blinker import signal

from app.spi.model import BaseModelResult
from utils import dict_utils
from utils.async_queue_utils import AsyncQueue
from utils.progress_utils import Progress
from utils.yaml_utils import (
    AsyncFileIoError,
    load_yaml,
    load_yaml_async,
    path_exists,
    run_coroutine_blocking,
    save_yaml,
    save_yaml_async,
    to_thread,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.data.timeline import TimelineItem
    from app.data.project import Project
    from app.data.story_board.shot_task_manager import ShotTaskManager


class Task:
    """
    Represents a single task with its configuration and state.

    A Task belongs to a TimelineItemTaskManager (for timeline tasks) or
    ShotTaskManager (for shot keyframe tasks) for storage, and reports
    progress through the ProjectTaskManager or ShotTaskExecutor.

    Shot tasks are identified by the explicit 'is_shot_task' flag in options.
    """

    def __init__(
        self,
        task_storage_manager: Union['TimelineItemTaskManager', 'ShotTaskManager'],
        progress_callback_manager: Union['ProjectTaskManager', 'ShotTaskExecutor'],
        path: str,
        options: Any,
    ):
        """
        Initialize a Task.

        Args:
            task_storage_manager: TimelineItemTaskManager or ShotTaskManager for storage
            progress_callback_manager: ProjectTaskManager or ShotTaskExecutor for progress callbacks
            path: Path to the task directory
            options: Task configuration options. For shot tasks, must contain 'is_shot_task': True
        """
        self.task_storage_manager = task_storage_manager
        self.progress_callback_manager = progress_callback_manager
        # Backward compatibility aliases
        self.timeline_item_task_manager = task_storage_manager
        self.project_task_manager = progress_callback_manager
        self.path = path
        self.config_path = os.path.join(self.path, "config.yml")
        self.options = options or {}

        # Extract properties from options
        self.task_id = os.path.basename(path)
        self.title = f'Task {self.task_id}'
        self.tool = self.options.get("tool", "txt2img")
        self.model = self.options.get("model", "comfyui")
        self.percent = self.options.get("percent", 0)
        self.status = self.options.get("status", "running")
        self.log = self.options.get("log", "")

        # Detect shot task ONLY from explicit flag (not from presence of shot_id)
        self._is_shot_task = bool(self.options.get("is_shot_task", False))

    @property
    def task_manager(self) -> 'ProjectTaskManager':
        """Backward compatibility: return progress callback manager"""
        return self.project_task_manager

    def get_config_path(self) -> str:
        return self.config_path

    def update_from_config(self):
        """Update task properties from config file"""
        if os.path.exists(self.config_path):
            config = load_yaml(self.config_path) or {}
            self.options.update(config)

            self.title = f'Task {self.task_id}'
            self.tool = config.get("task_type", config.get("tool", "txt2img"))
            self.model = self.options.get("model", "comfyui")
            self.percent = config.get("progress", config.get("percent", 0))
            self.status = config.get("status", "running")
            self.log = config.get("log", "")

    def is_shot_task(self) -> bool:
        """Check if this task is a shot keyframe task (requires explicit is_shot_task=True in options)."""
        return self._is_shot_task

    def get_shot_id(self) -> Optional[str]:
        """Get the shot ID if this is a shot task."""
        return self.options.get("shot_id")

    def get_scene_id(self) -> Optional[str]:
        """Get the scene ID if this is a shot task."""
        return self.options.get("scene_id")

    def get_shot_path(self) -> Optional[str]:
        """Get the shot directory path if this is a shot task."""
        return self.options.get("shot_path")


class TaskResult:
    """Represents the result of a completed task."""

    def __init__(self, task: Task, result: BaseModelResult):
        self.task = task
        self.result = result

    def get_timeline_index(self) -> int:
        """Get timeline index (only for timeline-based tasks)."""
        return self.task.options.get('timeline_index', -1)

    def get_timeline_item_id(self) -> int:
        """Get timeline item ID (only for timeline-based tasks)."""
        return self.task.options.get('timeline_item_id', self.task.options.get('timeline_index', -1))

    def get_shot_id(self) -> Optional[str]:
        """Get shot ID (only for shot-based tasks)."""
        return self.task.get_shot_id()

    def get_scene_id(self) -> Optional[str]:
        """Get scene ID (only for shot-based tasks)."""
        return self.task.get_scene_id()

    def is_shot_result(self) -> bool:
        """Check if this result is from a shot task."""
        return self.task.is_shot_task()

    def get_image_path(self) -> Optional[str]:
        return self.result.get_image_path()

    def get_video_path(self) -> Optional[str]:
        return self.result.get_video_path()

    def get_audio_path(self) -> Optional[str]:
        getter = getattr(self.result, "get_audio_path", None)
        if callable(getter):
            return getter()
        return None

    def get_task(self) -> Task:
        return self.task

    def get_task_id(self) -> str:
        return self.task.task_id


class TaskProgress(Progress):
    """Tracks progress of a running task."""

    def __init__(self, task: Task):
        super().__init__()
        self.task = task
        self.percent = 0
        self.logs = ''

    def on_progress(self, percent: int, logs: str):
        self.percent = percent
        self.logs = logs
        dict_utils.set_value(self.task.options, 'percent', percent)
        dict_utils.set_value(self.task.options, 'logs', logs)
        # Save progress to config file
        save_yaml(self.task.config_path, self.task.options)
        # Notify through project task manager
        self.task.project_task_manager.on_task_progress(self)


class ProjectTaskManager:
    """
    Project-level task manager for orchestrating task execution.

    Responsibilities:
    - Manage project-wide task signals (create, progress, finished)
    - Handle task execution queue
    - Coordinate task submission across timeline items
    - Provide signal connection methods for UI components
    """

    # Project-level signals
    task_create = signal("project_task_create")
    task_finished = signal("project_task_finished")
    task_progress = signal("project_task_progress")

    def __init__(self, project: 'Project'):
        """
        Initialize ProjectTaskManager.

        Args:
            project: The Project instance this manager belongs to
        """
        self.project = project

        # Task execution queue
        self.create_consumer = AsyncQueue()
        self.create_consumer.connect("create", self._on_create_task)
        self.execute_consumer = AsyncQueue()

    # Signal connection methods
    def connect_task_create(self, func):
        """Connect a handler to task creation events"""
        self.task_create.connect(func)

    def connect_task_execute(self, func):
        """Connect a handler to task execution events"""
        self.execute_consumer.connect("execute", func)

    def connect_task_progress(self, func):
        """Connect a handler to task progress events"""
        self.task_progress.connect(func)

    def connect_task_finished(self, func):
        """Connect a handler to task completion events"""
        self.task_finished.connect(func)

    def submit_task(self, options: dict, timeline_item_id: int = None):
        """
        Submit a new task for execution.

        The task will be stored in the specified timeline item's task manager.

        Args:
            options: Task configuration options
            timeline_item_id: The timeline item ID to associate with this task.
                             If None, uses the current timeline index.
        """
        # Use provided timeline_item_id or fall back to current timeline index
        if timeline_item_id is None:
            timeline_item_id = self.project.get_timeline_index()

        # Store both timeline_index and timeline_item_id in options
        # timeline_index is kept for backward compatibility
        options['timeline_index'] = timeline_item_id
        options['timeline_item_id'] = timeline_item_id

        self.create_consumer.add("create", options)

    async def _on_create_task(self, options: Any):
        """Internal handler for task creation from the queue"""
        # Get timeline_item_id from options (set at submission time)
        timeline_item_id = options.get('timeline_item_id')
        if timeline_item_id is None:
            logger.warning("⚠️ No timeline_item_id in task options, cannot create task")
            return

        # Get the specific timeline item by ID (not current item)
        timeline = self.project.get_timeline()
        timeline_item = timeline.get_item(timeline_item_id)

        if timeline_item is None:
            logger.warning(f"⚠️ Timeline item {timeline_item_id} not found, cannot create task")
            return

        # Get the timeline item's task manager
        item_task_manager = timeline_item.get_task_manager()

        # Create the task through the timeline item's task manager
        task = await item_task_manager.create_task(options, self)

        if task:
            # Emit task creation signal
            self.task_create.send(task)
            # Add to execution queue
            self.execute_consumer.add("execute", task)

    def on_task_progress(self, task_progress: TaskProgress):
        """Handle task progress update"""
        self.task_progress.send(task_progress)

    def on_task_finished(self, result: TaskResult):
        """Handle task completion"""
        self.task_finished.send(result)


class TimelineItemTaskManager:
    """
    Timeline-item-level task manager for task storage.

    Responsibilities:
    - Manage task storage for a specific timeline item
    - Handle task CRUD operations
    - Provide task listing and pagination
    """

    def __init__(self, timeline_item: 'TimelineItem', tasks_path: str):
        """
        Initialize TimelineItemTaskManager.

        Args:
            timeline_item: The TimelineItem instance this manager belongs to
            tasks_path: Path to the tasks directory for this timeline item
        """
        self.timeline_item = timeline_item
        self.tasks_path = tasks_path
        self.tasks: Dict[str, Task] = {}

        # Create tasks directory if it doesn't exist
        os.makedirs(self.tasks_path, exist_ok=True)

    @property
    def project(self) -> 'Project':
        """Get the project this task manager belongs to"""
        return self.timeline_item.timeline.project

    @property
    def project_task_manager(self) -> Optional[ProjectTaskManager]:
        """Get the project-level task manager"""
        return self.project.task_manager if self.project else None

    def _get_next_task_index(self) -> int:
        """Get the next task index for this timeline item"""
        task_index = self.timeline_item.get_config_value('task_index') or 0
        return task_index

    def _increment_task_index(self):
        """Increment the task index for this timeline item"""
        current = self._get_next_task_index()
        self.timeline_item.set_config_value('task_index', current + 1)

    async def create_task(self, options: Any, project_task_manager: ProjectTaskManager) -> Optional[Task]:
        """
        Create a new task and store it.

        Args:
            options: Task configuration options
            project_task_manager: The project-level task manager for callbacks

        Returns:
            The created Task, or None if creation failed
        """
        try:
            num = self._get_next_task_index()
            self._increment_task_index()

            task_fold_path = os.path.join(self.tasks_path, str(num))
            os.makedirs(task_fold_path, exist_ok=True)
            await save_yaml_async(os.path.join(task_fold_path, "config.yml"), options)

            task = Task(self, project_task_manager, task_fold_path, options)
            self.tasks[str(num)] = task

            return task
        except Exception as e:
            logger.error(f"❌ Error creating task: {e}", exc_info=True)
            return None

    def load_all_tasks(self) -> List[Task]:
        """
        Load all existing tasks from the tasks directory.

        Returns:
            List of loaded Task objects
        """
        try:
            return run_coroutine_blocking(self.load_all_tasks_async(apply=True))
        except Exception as e:
            logger.error(f"❌ Error loading tasks: {e}", exc_info=True)
            return []

    def load_all_tasks_thread_worker(self) -> List[Task]:
        """Load from disk using a fresh asyncio loop (call only from ``TaskManager`` pool threads)."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.load_all_tasks_async(apply=False))
            finally:
                loop.close()
                asyncio.set_event_loop(None)
        except Exception as e:
            logger.error(f"❌ Error loading tasks (worker): {e}", exc_info=True)
            return []

    def _collect_numeric_task_dirs(self) -> List[str]:
        if not os.path.exists(self.tasks_path):
            return []
        names: List[str] = []
        for d in os.listdir(self.tasks_path):
            dir_path = os.path.join(self.tasks_path, d)
            if os.path.isdir(dir_path) and d.isdigit():
                names.append(d)
        return names

    async def load_all_tasks_async(self, *, apply: bool = True) -> List[Task]:
        """Load tasks with async config reads (parallel I/O).

        When ``apply`` is False, returns tasks without mutating ``self.tasks`` (for background workers;
        caller must assign on the GUI thread).
        """
        if not await path_exists(self.tasks_path):
            logger.warning(f"⚠️ Tasks directory does not exist: {self.tasks_path}")
            return []

        try:
            task_dir_names = await to_thread(self._collect_numeric_task_dirs)
            if apply:
                self.tasks.clear()
            project_tm = self.project_task_manager

            async def load_one(task_dir_name: str) -> tuple[str, Task]:
                task_dir_path = os.path.join(self.tasks_path, task_dir_name)
                config_path = os.path.join(task_dir_path, "config.yml")
                options: Dict[str, Any] = {}
                if await path_exists(config_path):
                    try:
                        options = await load_yaml_async(config_path) or {}
                    except AsyncFileIoError as e:
                        logger.error("Task config invalid %s: %s", config_path, e)
                        options = {}
                return task_dir_name, Task(self, project_tm, task_dir_path, options)

            pairs = await asyncio.gather(*(load_one(d) for d in task_dir_names))
            loaded_tasks: List[Task] = []
            for name, task in pairs:
                if apply:
                    self.tasks[name] = task
                loaded_tasks.append(task)
            logger.info(f"✅ Loaded {len(loaded_tasks)} tasks from {self.tasks_path}")
            return loaded_tasks
        except Exception as e:
            logger.error(f"❌ Error loading tasks: {e}", exc_info=True)
            return []

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get a task by its ID"""
        if not self.tasks:
            self.load_all_tasks()
        return self.tasks.get(task_id)

    def get_all_tasks(self, start_index: int = 0, count: int = None) -> List[Task]:
        """
        Get all tasks with optional pagination.

        Args:
            start_index: Starting index for pagination
            count: Number of tasks to return (None for all)

        Returns:
            List of Task objects
        """
        # Load tasks if not already loaded
        if not self.tasks:
            self.load_all_tasks()

        all_task_ids = sorted(
            [task_id for task_id in self.tasks.keys() if task_id.isdigit()],
            key=lambda x: int(x),
            reverse=True
        )

        if count is None:
            task_ids_to_load = all_task_ids[start_index:]
        else:
            end_index = min(start_index + count, len(all_task_ids))
            task_ids_to_load = all_task_ids[start_index:end_index]

        return [self.tasks[task_id] for task_id in task_ids_to_load if task_id in self.tasks]

    def get_task_count(self) -> int:
        """Get the total number of tasks"""
        return len(self.tasks)

    def get_timeline_item_id(self) -> int:
        """Get the timeline item ID this manager belongs to"""
        return self.timeline_item.get_index()


# Backward compatibility aliases
TaskManager = TimelineItemTaskManager
