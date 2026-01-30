"""
Project Management Module

This module provides project and project manager classes for managing
Filmeto projects, including timeline, resources, characters, and tasks.
"""

import os.path
import os
from typing import List, Dict, Any, Callable, Optional
import time
import logging
from typing import List, Dict, Any
from datetime import datetime

from blinker import signal
from PySide6.QtCore import QTimer

from app.data.task import ProjectTaskManager, TimelineItemTaskManager, TaskResult
from app.data.timeline import Timeline
from app.data.drawing import Drawing
from app.data.resource import ResourceManager
from app.data.character import CharacterManager
from agent.chat.conversation import ConversationManager
from app.data.screen_play import ScreenPlayManager
from utils.yaml_utils import load_yaml, save_yaml

logger = logging.getLogger(__name__)


class Project:
    """
    Represents a Filmeto project.

    A project contains:
    - Timeline with multiple timeline items
    - Resources (images, videos, audio)
    - Characters
    - Task management (through ProjectTaskManager)
    """

    timeline_position = signal('timeline_position')

    def __init__(self, workspace, project_path: str, project_name: str, load_data: bool = True):
        """
        Initialize a Project.

        Args:
            workspace: The Workspace instance this project belongs to
            project_path: Path to the project directory
            project_name: Name of the project
            load_data: Whether to load project data immediately
        """
        self.workspace = workspace
        self.project_path = project_path
        self.project_name = project_name
        self.config = load_yaml(os.path.join(self.project_path, "project.yml")) or {}

        # Initialize Timeline first (needed by task manager)
        self.timeline = Timeline(self.workspace, self, os.path.join(self.project_path, 'timeline'))

        # Initialize ProjectTaskManager for project-level task orchestration
        self.task_manager = ProjectTaskManager(self)

        # Initialize other managers
        self.drawing = Drawing(self.workspace, self)
        self.resource_manager = ResourceManager(self.project_path)
        self.character_manager = CharacterManager(self.project_path, self.resource_manager)
        # Get the singleton instance
        from agent.chat.conversation import ConversationManager
        self.conversation_manager = ConversationManager()
        self.screenplay_manager = ScreenPlayManager(self.project_path)

        # If load_data is True, ensure actor data is loaded
        if load_data:
            # Trigger loading of actor data to ensure it's available immediately
            self.character_manager.list_characters()
        
        # Debounced save mechanism for high-frequency updates
        self._pending_save = False
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self._flush_config)

    # ==================== Task-related methods (delegate to ProjectTaskManager) ====================

    def connect_task_create(self, func: Callable):
        """Connect a handler to task creation events"""
        self.task_manager.connect_task_create(func)

    def connect_task_execute(self, func: Callable):
        """Connect a handler to task execution events"""
        self.task_manager.connect_task_execute(func)

    def connect_task_progress(self, func: Callable):
        """Connect a handler to task progress events"""
        self.task_manager.connect_task_progress(func)

    def connect_task_finished(self, func: Callable):
        """Connect a handler to task completion events"""
        self.task_manager.connect_task_finished(func)

    def submit_task(self, params: dict, timeline_item_id: int = None):
        """
        Submit a task for execution.
        
        Args:
            params: Task configuration parameters
            timeline_item_id: The timeline item ID to associate with this task.
                             If None, uses the current timeline index.
        """
        # Use provided timeline_item_id or fall back to current timeline index
        if timeline_item_id is None:
            timeline_item_id = self.get_timeline_index()
        
        logger.info(f"Submitting task for timeline_item {timeline_item_id}: {params}")
        self.task_manager.submit_task(params, timeline_item_id)

    def on_task_finished(self, result: TaskResult):
        """Handle task completion - register resources and update timeline"""
        self._register_task_resources(result)
        self.timeline.on_task_finished(result)
        self.task_manager.on_task_finished(result)

    def _register_task_resources(self, result: TaskResult):
        """Register AI-generated outputs as resources"""
        task = result.get_task()
        task_id = result.get_task_id()

        task_options = task.options
        tool = task_options.get('tool', '')
        model = task_options.get('model', '')
        prompt = task_options.get('prompt', '')

        registered_resources = []
        
        # Register image output if exists
        image_path = result.get_image_path()
        if image_path and os.path.exists(image_path):
            additional_metadata = {
                'prompt': prompt,
                'model': model,
                'tool': tool,
                'task_id': task_id
            }
            resource = self.resource_manager.add_resource(
                source_file_path=image_path,
                source_type='ai_generated',
                source_id=task_id,
                additional_metadata=additional_metadata
            )
            if resource:
                logger.info(f"✅ Registered image resource: {resource.name}")
                registered_resources.append({
                    'type': 'image',
                    'resource_path': resource.file_path,
                    'resource_name': resource.name,
                    'resource_id': resource.resource_id
                })
        
        # Register video output if exists
        video_path = result.get_video_path()
        if video_path and os.path.exists(video_path):
            additional_metadata = {
                'prompt': prompt,
                'model': model,
                'tool': tool,
                'task_id': task_id
            }
            resource = self.resource_manager.add_resource(
                source_file_path=video_path,
                source_type='ai_generated',
                source_id=task_id,
                additional_metadata=additional_metadata
            )
            if resource:
                logger.info(f"✅ Registered video resource: {resource.name}")
                registered_resources.append({
                    'type': 'video',
                    'resource_path': resource.file_path,
                    'resource_name': resource.name,
                    'resource_id': resource.resource_id
                })
        
        # Update task config with resource paths
        if registered_resources:
            self._update_task_config_with_resources(task, registered_resources)

    def _update_task_config_with_resources(self, task, registered_resources: List[Dict]):
        """Update task config.yml with resource information"""
        try:
            task_config = load_yaml(task.config_path) or {}
            task_config['status'] = 'success'
            task_config['resources'] = registered_resources

            for resource_info in registered_resources:
                if resource_info['type'] == 'image':
                    task_config['image_resource_path'] = resource_info['resource_path']
                    task_config['image_resource_name'] = resource_info['resource_name']
                elif resource_info['type'] == 'video':
                    task_config['video_resource_path'] = resource_info['resource_path']
                    task_config['video_resource_name'] = resource_info['resource_name']

            save_yaml(task.config_path, task_config)
            task.options.update(task_config)

            logger.info(f"✅ Updated task config.yml with resource paths for task {task.task_id}")
        except Exception as e:
            logger.error(f"❌ Error updating task config.yml: {e}", exc_info=True)

    # ==================== Timeline-related methods ====================

    def connect_timeline_switch(self, func: Callable):
        """Connect a handler to timeline switch events"""
        self.timeline.connect_timeline_switch(func)

    def connect_layer_changed(self, func: Callable):
        """Connect a handler to layer changed events"""
        self.timeline.connect_layer_changed(func)

    def connect_timeline_changed(self, func: Callable):
        """Connect to timeline_changed signal"""
        self.timeline.connect_timeline_changed(func)

    def connect_timeline_position(self, func: Callable):
        """Connect a handler to timeline position changes"""
        self.timeline_position.connect(func)

    def get_timeline(self) -> Timeline:
        """Get the timeline instance"""
        return self.timeline

    def get_timeline_index(self) -> int:
        """Get the current timeline index"""
        return self.config.get('timeline_index', 0)

    def get_timeline_position(self) -> float:
        """Get the current timeline playback position (seconds)"""
        return self.config.get('timeline_position', 0.0)

    def set_timeline_position(self, position: float, flush: bool = False) -> bool:
        """
        Set the timeline playback position.

        Args:
            position: Position in seconds
            flush: Whether to immediately write to file

        Returns:
            True if position was set successfully
        """
        if position < 0:
            return False

        timeline_duration = self.calculate_timeline_duration()
        if position > timeline_duration:
            return False

        position = round(position, 3)
        self.config['timeline_position'] = position

        if flush:
            self._flush_config()
        else:
            self._pending_save = True
            self._save_timer.start()

        self.timeline_position.send(position)
        return True

    def get_timeline_duration(self) -> float:
        """Get the total timeline duration (seconds)"""
        return self.config.get('timeline_duration', 0.0)

    def set_timeline_duration(self, duration: float):
        """Set the total timeline duration"""
        self.update_config('timeline_duration', duration)

    def get_item_duration(self, item_index: int) -> float:
        """Get duration for a specific timeline item"""
        item_durations = self.config.get('timeline_item_durations', {})
        return item_durations.get(str(item_index), 1.0)

    def set_item_duration(self, item_index: int, duration: float):
        """Set duration for a specific timeline item"""
        if 'timeline_item_durations' not in self.config:
            self.config['timeline_item_durations'] = {}
        self.config['timeline_item_durations'][str(item_index)] = duration
        save_yaml(os.path.join(self.project_path, "project.yml"), self.config)

    def has_item_duration(self, item_index: int) -> bool:
        """Check if duration is set for a specific timeline item"""
        item_durations = self.config.get('timeline_item_durations', {})
        return str(item_index) in item_durations

    def calculate_timeline_duration(self) -> float:
        """Calculate total timeline duration by summing all item durations"""
        item_durations = self.config.get('timeline_item_durations', {})
        return sum(item_durations.values())

    # ==================== Config management ====================

    def get_config(self) -> dict:
        """Get the project configuration"""
        return self.config

    def _flush_config(self):
        """Flush pending config changes to disk"""
        if self._pending_save:
            save_yaml(os.path.join(self.project_path, "project.yml"), self.config)
            self._pending_save = False

    def update_config(self, key: str, value: Any, debounced: bool = False):
        """
        Update a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
            debounced: Whether to use debounced save
        """
        self.config[key] = value
        if debounced:
            self._pending_save = True
            self._save_timer.start()
        else:
            save_yaml(os.path.join(self.project_path, "project.yml"), self.config)

    # ==================== Resource accessors ====================

    def get_drawing(self) -> Drawing:
        """Get the drawing instance"""
        return self.drawing

    def get_resource_manager(self) -> ResourceManager:
        """Get the resource manager instance"""
        return self.resource_manager

    def get_character_manager(self) -> CharacterManager:
        """Get the actor manager instance"""
        return self.character_manager

    def get_conversation_manager(self) -> ConversationManager:
        """Get the conversation manager instance"""
        return self.conversation_manager

    def create_conversation(self, title: Optional[str] = None):
        """Create a conversation in this project."""
        return self.conversation_manager.create_conversation(self.project_path, title)

    def get_conversation(self, conversation_id: str):
        """Get a conversation from this project."""
        return self.conversation_manager.get_conversation(self.project_path, conversation_id)

    def save_conversation(self, conversation):
        """Save a conversation in this project."""
        return self.conversation_manager.save_conversation(self.project_path, conversation)

    def list_conversations(self):
        """List conversations in this project."""
        return self.conversation_manager.list_conversations(self.project_path)

    def delete_conversation(self, conversation_id: str):
        """Delete a conversation from this project."""
        return self.conversation_manager.delete_conversation(self.project_path, conversation_id)

    def add_message_to_conversation(self, conversation_id: str, message):
        """Add a message to a conversation in this project."""
        return self.conversation_manager.add_message(self.project_path, conversation_id, message)

    def get_or_create_default_conversation(self):
        """Get or create a default conversation in this project."""
        return self.conversation_manager.get_or_create_default_conversation(self.project_path)

    def get_screenplay_manager(self) -> 'ScreenPlayManager':
        """Get the screenplay manager instance"""
        return self.screenplay_manager

    def get_current_timeline_item_task_manager(self) -> Optional[TimelineItemTaskManager]:
        """Get the task manager for the current timeline item"""
        current_item = self.timeline.get_current_item()
        if current_item:
            return current_item.get_task_manager()
        return None

    def get_language(self) -> str:
        """
        Get the language setting for this project.
        Prioritizes the language from project.yml with key "language".

        Returns:
            Language code for the project (default: 'en_US')
        """
        # First, try to get language from project.yml
        project_language = self.config.get("language")
        if project_language:
            # Convert language code to our format (en -> en_US, zh -> zh_CN)
            if project_language == "zh_CN" or project_language == "zh":
                return "zh_CN"
            else:
                return "en_US"

        # Fallback: try to get language from workspace settings
        if not self.workspace or not hasattr(self.workspace, 'settings'):
            return 'en_US'

        try:
            language = self.workspace.settings.get("general.language", "en")
            # Convert language code to our format (en -> en_US, zh -> zh_CN)
            if language == "zh_CN":
                return "zh_CN"
            elif language == "zh":
                return "zh_CN"
            else:
                return "en_US"
        except:
            # If settings are not available, default to en_US
            return "en_US"


class ProjectManager:
    """
    Manages multiple projects with CRUD operations.
    """

    project_switched = signal('project_switched')
    
    def __init__(self, workspace_root_path: str, defer_scan: bool = False):
        """
        Initialize ProjectManager.

        Args:
            workspace_root_path: Path to the workspace root directory
        """
        self.workspace_root_path = workspace_root_path
        # Define the projects subdirectory path
        self.projects_dir = os.path.join(workspace_root_path, "projects")
        self.projects: Dict[str, Project] = {}
        self._defer_scan = defer_scan

        # Create the projects directory if it doesn't exist
        os.makedirs(self.projects_dir, exist_ok=True)

        if not defer_scan:
            self._load_projects()
    
    def _load_projects(self):
        """Load all projects from the projects subdirectory"""
        # Don't create the projects directory here to avoid early creation
        if not os.path.exists(self.projects_dir):
            logger.info(f"⏱️  [ProjectManager] Projects directory does not exist: {self.projects_dir}")
            return

        scan_start = time.time()
        logger.info(f"⏱️  [ProjectManager] Scanning projects directory: {self.projects_dir}")
        items = os.listdir(self.projects_dir)
        scan_time = (time.time() - scan_start) * 1000
        logger.info(f"⏱️  [ProjectManager] Directory scan completed in {scan_time:.2f}ms (found {len(items)} items)")

        loaded_count = 0
        failed_count = 0
        for item in items:
            project_path = os.path.join(self.projects_dir, item)
            if os.path.isdir(project_path):
                project_config_path = os.path.join(project_path, "project.yml")
                if os.path.exists(project_config_path):
                    try:
                        project_start = time.time()
                        # 这里我们假设项目目录名就是项目名
                        # 修改为不自动加载项目数据，只在需要时加载
                        project = Project(self.workspace_root_path, project_path, item, load_data=False)
                        self.projects[item] = project
                        project_time = (time.time() - project_start) * 1000
                        logger.info(f"⏱️  [ProjectManager] Loaded project '{item}' in {project_time:.2f}ms")
                        loaded_count += 1
                    except Exception as e:
                        logger.error(f"Failed to load project {item}: {e}")
                        logger.error(f"⏱️  [ProjectManager] Failed to load project '{item}': {e}")
                        failed_count += 1

        logger.info(f"⏱️  [ProjectManager] Project loading summary: {loaded_count} loaded, {failed_count} failed")

    def ensure_projects_loaded(self):
        """Ensure projects are loaded (for deferred loading)"""
        # Create the projects directory if it doesn't exist
        os.makedirs(self.projects_dir, exist_ok=True)

        # Track whether projects were loaded initially
        projects_already_loaded = bool(self.projects)

        if self._defer_scan and not projects_already_loaded:
            load_start = time.time()
            logger.info(f"⏱️  [ProjectManager] Starting deferred project scan...")
            self._load_projects()

            load_time = (time.time() - load_start) * 1000
            project_count = len(self.projects)
            logger.info(f"⏱️  [ProjectManager] Deferred project scan completed in {load_time:.2f}ms (found {project_count} projects)")
        elif self._defer_scan and projects_already_loaded:
            # If we're in deferred mode but some projects are already loaded,
            # we still need to load all projects from disk
            load_start = time.time()
            logger.info(f"⏱️  [ProjectManager] Loading all projects from disk (some already loaded)...")
            self._load_projects()

            load_time = (time.time() - load_start) * 1000
            project_count = len(self.projects)
            logger.info(f"⏱️  [ProjectManager] Project scan completed in {load_time:.2f}ms (found {project_count} projects)")

    def create_project(self, project_name: str) -> Project:
        """
        Create a new project.

        Args:
            project_name: Name of the project

        Returns:
            The created Project instance

        Raises:
            ValueError: If project already exists
        """
        project_path = os.path.join(self.projects_dir, project_name)

        if project_name in self.projects:
            raise ValueError(f"Project {project_name} already exists")

        if os.path.exists(project_path):
            raise ValueError(f"Project path {project_path} already exists")

        # Create project directory structure
        os.makedirs(project_path, exist_ok=True)

        # Create project configuration
        project_config = {
            "project_name": project_name,
            "created_at": datetime.now().isoformat(),
            "timeline_index": 0,
            "timeline_position": 0.0,
            "timeline_duration": 0.0,
            "timeline_item_durations": {}
        }
        save_yaml(os.path.join(project_path, "project.yml"), project_config)

        # Create directory structure
        os.makedirs(os.path.join(project_path, "timeline"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "prompts"), exist_ok=True)

        resources_path = os.path.join(project_path, "resources")
        os.makedirs(resources_path, exist_ok=True)
        for subdir in ["images", "videos", "audio", "others"]:
            os.makedirs(os.path.join(resources_path, subdir), exist_ok=True)

        os.makedirs(os.path.join(project_path, "characters"), exist_ok=True)

        agent_path = os.path.join(project_path, "agent")
        os.makedirs(agent_path, exist_ok=True)
        os.makedirs(os.path.join(agent_path, "chats"), exist_ok=True)  # Changed from "conversations" to "chats"
        os.makedirs(os.path.join(agent_path, "crew_members"), exist_ok=True)

        # Create project instance
        project = Project(self.workspace_root_path, project_path, project_name)
        self.projects[project_name] = project

        try:
            from agent.crew import CrewService

            CrewService().initialize_project_crew_members(project)
        except Exception as exc:
            logger.warning(f"Failed to initialize crew_members for project {project_name}: {exc}")

        return project
    
    def get_project(self, project_name: str) -> Optional[Project]:
        """Get a project by name"""
        return self.projects.get(project_name)
    
    def list_projects(self) -> List[str]:
        """List all project names"""
        # Ensure projects are loaded before returning the list
        self.ensure_projects_loaded()
        return list(self.projects.keys())
    
    def delete_project(self, project_name: str) -> bool:
        """
        Delete a project.

        Args:
            project_name: Name of the project to delete

        Returns:
            True if deletion was successful
        """
        if project_name not in self.projects:
            return False
        
        project = self.projects[project_name]
        project_path = project.project_path

        del self.projects[project_name]

        try:
            import shutil
            shutil.rmtree(project_path)
            return True
        except Exception as e:
            logger.error(f"Failed to delete project {project_name}: {e}")
            return False
    
    def update_project(self, project_name: str, new_config: Dict[str, Any]) -> bool:
        """Update project configuration"""
        if project_name not in self.projects:
            return False
        
        project = self.projects[project_name]
        for key, value in new_config.items():
            project.update_config(key, value)
        
        return True
    
    def switch_project(self, project_name: str) -> Optional[Project]:
        """
        Switch to a project and emit signal.

        Args:
            project_name: Name of the project to switch to

        Returns:
            The switched Project instance, or None if not found
        """
        if project_name in self.projects:
            project = self.projects[project_name]
            self.project_switched.send(project_name)
            return project
        return None

