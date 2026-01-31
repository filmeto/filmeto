"""
Path utility functions for Filmeto.
"""

import os
from pathlib import Path
from typing import Optional


def get_workspace_path() -> Path:
    """
    Get the default workspace path.

    Returns:
        Path to the workspace directory
    """
    # Check if workspace environment variable is set
    workspace_env = os.environ.get("FILMETO_WORKSPACE")
    if workspace_env:
        return Path(workspace_env)

    # Check if there's a workspace directory in the current directory
    current_dir = Path.cwd()
    workspace_dir = current_dir / "workspace"
    if workspace_dir.exists():
        return workspace_dir

    # Default to workspace in the user's home directory
    home_workspace = Path.home() / "filmeto" / "workspace"
    return home_workspace


def get_project_path(project_name: str, workspace_path: Optional[Path] = None) -> Path:
    """
    Get the path to a project directory.

    Args:
        project_name: Name of the project
        workspace_path: Path to the workspace. If None, uses default workspace.

    Returns:
        Path to the project directory
    """
    if workspace_path is None:
        workspace_path = get_workspace_path()

    return workspace_path / "projects" / project_name


def ensure_project_dirs(project_path: Path) -> None:
    """
    Ensure all necessary project directories exist.

    Args:
        project_path: Path to the project directory
    """
    directories = [
        project_path / "screen_plays",
        project_path / "scripts",
        project_path / "assets",
        project_path / "exports",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
