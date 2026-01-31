"""
ScreenPlayManager Factory module for Filmeto.

This module provides a factory for getting ScreenPlayManager instances
based on workspace and project_name, ensuring project isolation.
"""

import os
from pathlib import Path
from typing import Dict, Optional, Union
from threading import Lock

from .screen_play_manager import ScreenPlayManager


class ScreenPlayManagerFactory:
    """
    Factory for managing ScreenPlayManager instances with project isolation.

    Each unique (workspace_path, project_name) combination gets its own
    ScreenPlayManager instance, ensuring projects don't interfere with each other.
    """

    _instances: Dict[tuple, ScreenPlayManager] = {}
    _lock = Lock()

    @classmethod
    def get_manager(
        cls,
        project_name: str,
        workspace_path: Optional[Union[str, Path]] = None
    ) -> ScreenPlayManager:
        """
        Get or create a ScreenPlayManager for the specified project.

        Args:
            project_name: Name of the project
            workspace_path: Path to the workspace directory. If None, uses current workspace.

        Returns:
            ScreenPlayManager instance for the specified project

        Example:
            manager = ScreenPlayManagerFactory.get_manager("my_project")
            manager.create_scene("scene_001", "Opening", "# INT. ROOM - DAY")
        """
        # Resolve workspace path
        if workspace_path is None:
            # Try to get workspace from environment or use default
            from utils.path_utils import get_workspace_path
            workspace_path = get_workspace_path()

        workspace_path = Path(workspace_path)

        # Create the project path
        project_path = workspace_path / "projects" / project_name

        # Ensure project directory exists
        project_path.mkdir(parents=True, exist_ok=True)

        # Create a unique key for this combination
        key = (str(workspace_path), project_name)

        # Get or create instance (thread-safe)
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = ScreenPlayManager(project_path)
            return cls._instances[key]

    @classmethod
    def get_manager_by_path(
        cls,
        project_path: Union[str, Path]
    ) -> ScreenPlayManager:
        """
        Get or create a ScreenPlayManager for the specified project path.

        This method doesn't use caching and creates a new instance each time,
        useful for cases where you have a direct project path.

        Args:
            project_path: Path to the project directory

        Returns:
            ScreenPlayManager instance for the specified project path
        """
        return ScreenPlayManager(project_path)

    @classmethod
    def remove_manager(
        cls,
        project_name: str,
        workspace_path: Optional[Union[str, Path]] = None
    ) -> bool:
        """
        Remove a cached ScreenPlayManager instance.

        Args:
            project_name: Name of the project
            workspace_path: Path to the workspace directory

        Returns:
            True if the instance was removed, False otherwise
        """
        # Resolve workspace path
        if workspace_path is None:
            from utils.path_utils import get_workspace_path
            workspace_path = get_workspace_path()

        workspace_path = Path(workspace_path)
        key = (str(workspace_path), project_name)

        with cls._lock:
            if key in cls._instances:
                del cls._instances[key]
                return True
            return False

    @classmethod
    def clear_all(cls):
        """Clear all cached ScreenPlayManager instances."""
        with cls._lock:
            cls._instances.clear()

    @classmethod
    def list_cached_managers(cls) -> Dict[tuple, str]:
        """
        List all cached ScreenPlayManager instances.

        Returns:
            Dictionary mapping (workspace_path, project_name) tuples to their project paths
        """
        result = {}
        for (workspace_path, project_name), manager in cls._instances.items():
            result[(workspace_path, project_name)] = str(manager.project_path)
        return result


# Convenience function for getting a manager
def get_screenplay_manager(
    project_name: str,
    workspace_path: Optional[Union[str, Path]] = None
) -> ScreenPlayManager:
    """
    Convenience function to get a ScreenPlayManager for a project.

    Args:
        project_name: Name of the project
        workspace_path: Path to the workspace directory

    Returns:
        ScreenPlayManager instance
    """
    return ScreenPlayManagerFactory.get_manager(project_name, workspace_path)
