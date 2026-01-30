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

import os
import logging
from typing import Any, Optional, Dict, List, TYPE_CHECKING
import threading
from typing import Any, List

from blinker import signal

from app.spi.model import BaseModelResult
from utils import dict_utils
from utils.async_queue_utils import AsyncQueue
from utils.progress_utils import Progress
from utils.yaml_utils import load_yaml, save_yaml

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.data.timeline import TimelineItem
    from app.data.project import Project


class Task:
    """
    Represents a single task with its configuration and state.

    A Task belongs to a TimelineItemTaskManager for storage,
    but reports progress through the ProjectTaskManager.
    """

    def __init__(self, timeline_item_task_manager: 'TimelineItemTaskManager',
                 project_task_manager: 'ProjectTaskManager',
                 path: str, options: Any):
        """
        Initialize a Task.

        Args:
            timeline_item_task_manager: The TimelineItemTaskManager for storage
            project_task_manager: The ProjectTaskManager for progress callbacks
            path: Path to the task directory
            options: Task configuration options
        """
        self.timeline_item_task_manager = timeline_item_task_manager
        self.project_task_manager = project_task_manager
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

    @property
    def task_manager(self) -> 'ProjectTaskManager':
        """Backward compatibility: return project task manager for progress callbacks"""
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


class TaskResult:
    """Represents the result of a completed task."""

    def __init__(self, task: Task, result: BaseModelResult):
        self.task = task
        self.result = result

    def get_timeline_index(self) -> int:
        return self.task.options['timeline_index']

    def get_timeline_item_id(self) -> int:
        return self.task.options.get('timeline_item_id', self.task.options.get('timeline_index'))

    def get_image_path(self) -> Optional[str]:
        return self.result.get_image_path()

    def get_video_path(self) -> Optional[str]:
        return self.result.get_video_path()

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

    def _ensure_loaded(self):
        """Ensure tasks are loaded from disk"""
        if not self._loaded:
            with self._load_lock:
                if not self._loaded:
                    self.load_all_tasks()
                    self._loaded = True

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
            save_yaml(os.path.join(task_fold_path, "config.yml"), options)

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
        if not os.path.exists(self.tasks_path):
            logger.warning(f"⚠️ Tasks directory does not exist: {self.tasks_path}")
            return []

        try:
            # Get all task directories (numbered folders)
            task_dirs = []
            for d in os.listdir(self.tasks_path):
                dir_path = os.path.join(self.tasks_path, d)
                if os.path.isdir(dir_path) and d.isdigit():
                    task_dirs.append(d)

            # Clear existing tasks before loading
            self.tasks.clear()

            # Load each task
            loaded_tasks = []
            project_tm = self.project_task_manager

            for task_dir_name in task_dirs:
                task_dir_path = os.path.join(self.tasks_path, task_dir_name)
                
                # Load config file for the task
                config_path = os.path.join(task_dir_path, "config.yml")
                options = {}
                if os.path.exists(config_path):
                    options = load_yaml(config_path) or {}
                
                # Create Task object
                task = Task(self, project_tm, task_dir_path, options)
                self.tasks[task_dir_name] = task
                loaded_tasks.append(task)
            
            logger.info(f"✅ Loaded {len(loaded_tasks)} tasks from {self.tasks_path}")
            return loaded_tasks

        except Exception as e:
            logger.error(f"❌ Error loading tasks: {e}", exc_info=True)
            return []

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get a task by its ID"""
        self._ensure_loaded()
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
