import asyncio
import os
import time
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path

from app.data.project import Project, ProjectManager
from app.data.task import TaskResult
from app.data.prompt import PromptManager, PromptTemplate
from app.data.settings import Settings
from utils.yaml_utils import load_yaml, save_yaml

logger = logging.getLogger(__name__)


class Workspace():

    @property
    def project(self) -> Project:
        self._ensure_bootstrap_project()
        return self._project

    @project.setter
    def project(self, value: Project):
        self._project = value

    def __init__(self, workspace_path:str, project_name:str, load_data:bool = True, defer_heavy_init:bool = False):
        init_start = time.time()
        logger.info(f"⏱️  [Workspace] Starting initialization (defer_heavy_init={defer_heavy_init})...")

        self.workspace_path = workspace_path
        self.project_name = project_name
        # Update project path to be inside the projects subdirectory
        projects_dir = os.path.join(workspace_path, "projects")
        self.project_path = os.path.join(projects_dir, self.project_name)
        self._defer_heavy_init = defer_heavy_init

        # Initialize ProjectManager first (to handle project creation/loading)
        pm_start = time.time()
        logger.info(f"⏱️  [Workspace] Creating ProjectManager (defer_scan={defer_heavy_init})...")
        self.project_manager = ProjectManager(workspace_path, defer_scan=defer_heavy_init)

        self._project = None
        if defer_heavy_init:
            projects_dir = os.path.join(workspace_path, "projects")
            project_path_on_disk = os.path.join(projects_dir, project_name)
            if not os.path.exists(project_path_on_disk):
                logger.info(f"Project {project_name} does not exist, creating new project...")
                self._project = self.project_manager.create_project(project_name)
            else:
                logger.info(
                    f"Project {project_name} on disk; full Project instance deferred "
                    f"(saves heavy init before first UI access)"
                )
        else:
            loaded = self.project_manager.get_project(project_name)
            if loaded is None:
                projects_dir = os.path.join(workspace_path, "projects")
                project_path_on_disk = os.path.join(projects_dir, project_name)
                if os.path.exists(project_path_on_disk):
                    logger.info(f"Project {project_name} exists on disk, loading it...")
                    self._project = Project(
                        self, project_path_on_disk, project_name, load_data=load_data
                    )
                    self.project_manager.projects[project_name] = self._project
                else:
                    logger.info(f"Project {project_name} does not exist, creating new project...")
                    self._project = self.project_manager.create_project(project_name)
            else:
                logger.info(f"Project {project_name} already exists, loading existing project...")
                self._project = loaded

        pm_time = (time.time() - pm_start) * 1000
        logger.info(f"⏱️  [Workspace] ProjectManager ready in {pm_time:.2f}ms")

        # Initialize PromptManager (lightweight - just sets up directory)
        prompt_start = time.time()
        logger.info(f"⏱️  [Workspace] Creating PromptManager...")
        prompts_dir = os.path.join(self.project_path, 'prompts')
        self.prompt_manager = PromptManager(prompts_dir)
        prompt_time = (time.time() - prompt_start) * 1000
        logger.info(f"⏱️  [Workspace] PromptManager created in {prompt_time:.2f}ms")

        # Initialize Settings (defer heavy loading if requested)
        settings_start = time.time()
        logger.info(f"⏱️  [Workspace] Creating Settings (defer_load={defer_heavy_init})...")
        self.settings = Settings(workspace_path, defer_load=defer_heavy_init)
        settings_time = (time.time() - settings_start) * 1000
        logger.info(f"⏱️  [Workspace] Settings created in {settings_time:.2f}ms")

        # Initialize Plugins (defer discovery if requested)
        plugins_start = time.time()
        logger.info(f"⏱️  [Workspace] Creating Plugins (defer_discovery={defer_heavy_init})...")
        from app.plugins.plugins import Plugins
        self.plugins = Plugins(self, defer_discovery=defer_heavy_init)
        plugins_time = (time.time() - plugins_start) * 1000
        logger.info(f"⏱️  [Workspace] Plugins created in {plugins_time:.2f}ms")

        total_time = (time.time() - init_start) * 1000
        logger.info(f"⏱️  [Workspace] Initialization complete in {total_time:.2f}ms")
        return

    def _ensure_bootstrap_project(self) -> None:
        """Instantiate the default project when defer_heavy_init left it unloaded."""
        if self._project is not None:
            return
        if not getattr(self, "_defer_heavy_init", False):
            return
        pn = self.project_name
        pp = os.path.join(self.workspace_path, "projects", pn)
        if not os.path.exists(pp):
            self._project = self.project_manager.create_project(pn)
            return
        logger.info("⏱️  [Workspace] Lazy-loading project '%s' on first access", pn)
        t0 = time.time()
        self._project = Project(self, pp, pn, load_data=False)
        self.project_manager.projects[pn] = self._project
        logger.info(
            "⏱️  [Workspace] Lazy project init done in %.2fms", (time.time() - t0) * 1000
        )

    def get_project(self):
        """Get the current project instance."""
        return self.project

    def get_project_manager(self):
        return self.project_manager

    def get_prompt_manager(self) -> PromptManager:
        """Get the prompt manager instance"""
        return self.prompt_manager
    
    def get_settings(self) -> Settings:
        """Get the settings instance"""
        return self.settings

    def connect_task_create(self, func):
        self.project.connect_task_create(func)

    def connect_task_execute(self, func):
        self.project.connect_task_execute(func)

    def connect_task_progress(self, func):
        self.project.connect_task_progress(func)

    def connect_task_finished(self, func):
        self.project.connect_task_finished(func)

    def connect_timeline_switch(self, func):
        self.project.connect_timeline_switch(func)

    def connect_layer_changed(self, func):
        self.project.connect_layer_changed(func)

    def connect_project_switched(self, func: Callable):
        self.project_manager.project_switched.connect(func)

    def connect_timeline_position(self, func: Callable):
        self.project.connect_timeline_position(func)

    def submit_task(self, params: dict, timeline_item_id: int = None):
        """
        Submit a task for execution.

        Args:
            params: Task configuration parameters
            timeline_item_id: The timeline item ID to associate with this task.
                             If None, uses the current timeline index.
        """
        logger.info(f"Workspace submitting task: {params}")
        self.project.submit_task(params, timeline_item_id)

    def on_task_finished(self,result:TaskResult):
        self.project.on_task_finished(result)

    def switch_project(self, project_name: str):
        """切换到指定项目"""
        # 更新项目路径和名称
        self.project_name = project_name
        # Update project path to be inside the projects subdirectory
        projects_dir = os.path.join(self.workspace_path, "projects")
        self.project_path = os.path.join(projects_dir, project_name)

        # 创建新项目实例（不自动加载数据）
        new_project = Project(self, self.project_path, project_name, load_data=False)

        # 替换当前项目
        self.project = new_project

        # 更新PromptManager
        prompts_dir = os.path.join(self.project_path, 'prompts')
        self.prompt_manager = PromptManager(prompts_dir)

        # 使用ProjectManager切换项目并发送信号
        # 注意：必须在更新完所有状态后再发送信号，确保监听者能获取到正确的项目状态
        switched_project = self.project_manager.switch_project(project_name)

        logger.info(f"切换到项目: {project_name}")
        return self.project

    def switch_project_lightweight(self, project_name: str):
        """Lightweight project switch for fast window transition"""
        # 更新项目路径和名称
        self.project_name = project_name
        projects_dir = os.path.join(self.workspace_path, "projects")
        self.project_path = os.path.join(projects_dir, project_name)

        # Create project with minimal initialization (defer heavy loading)
        new_project = Project(self, self.project_path, project_name, load_data=False)

        # 替换当前项目
        self.project = new_project

        # Update PromptManager
        prompts_dir = os.path.join(self.project_path, 'prompts')
        self.prompt_manager = PromptManager(prompts_dir)

        # Use ProjectManager to switch (lightweight)
        self.project_manager.switch_project(project_name)

        logger.info(f"Lightweight switch to project: {project_name}")
        return self.project

    def _async_load_project_data(self):
        """Asynchronously load project data after window is displayed"""
        if not self.project:
            return

        logger.info("Starting async load of project data...")
        from PySide6.QtCore import QTimer

        # Defer loading managers data
        QTimer.singleShot(0, self._load_project_managers_data)

    def _load_project_managers_data(self):
        """Load managers data in background"""
        if not self.project:
            return

        # Load character manager data
        if hasattr(self.project, 'character_manager'):
            self.project.character_manager.list_characters()

        # Load resource manager data
        if hasattr(self.project, 'resource_manager'):
            self.project.resource_manager.get_all()

        logger.info("Project managers data loaded")

    def get_path(self) -> str:
        """
        Get the workspace path.

        Returns:
            The workspace path as a string.
        """
        return self.workspace_path

    def get_current_timeline_item(self):
        return self.project.get_timeline().get_current_item()
