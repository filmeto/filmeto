"""
Filmeto Agent Instance Manager Module

Manages singleton instances of FilmetoAgent for different workspace/project combinations.
"""
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

from agent.core.filmeto_utils import get_workspace_path_safe, get_project_from_workspace

if TYPE_CHECKING:
    from agent.filmeto_agent import FilmetoAgent

logger = logging.getLogger(__name__)


class FilmetoInstanceManager:
    """
    Manages FilmetoAgent singleton instances.
    Each unique (workspace_path, project_name) combination gets its own instance.
    """

    # Class-level instance storage: dict[instance_key] -> FilmetoAgent
    _instances: Dict[str, "FilmetoAgent"] = {}
    _lock = False  # Simple lock for thread safety

    @classmethod
    def get_instance(
        cls,
        workspace: Any,
        project_name: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        streaming: bool = True,
    ) -> "FilmetoAgent":
        """
        Get or create a FilmetoAgent instance for the given workspace and project.

        Args:
            workspace: The workspace object
            project_name: The name of the project
            model: The LLM model to use (only used when creating new instance)
            temperature: The temperature setting (only used when creating new instance)
            streaming: Whether to use streaming (only used when creating new instance)

        Returns:
            FilmetoAgent: The agent instance for this workspace/project combination
        """
        from agent.filmeto_agent import FilmetoAgent

        # Extract workspace path for key generation
        workspace_path = get_workspace_path_safe(workspace)

        # Create instance key
        instance_key = f"{workspace_path}:{project_name}"

        # Check if instance already exists
        if instance_key in cls._instances:
            logger.debug(f"Reusing existing FilmetoAgent instance for {instance_key}")
            return cls._instances[instance_key]

        # Create new instance
        logger.info(f"Creating new FilmetoAgent instance for {instance_key}")

        # Get project object from workspace
        project = get_project_from_workspace(workspace, project_name)

        agent = FilmetoAgent(
            workspace=workspace,
            project=project,
            model=model,
            temperature=temperature,
            streaming=streaming,
        )

        # Store instance
        cls._instances[instance_key] = agent
        return agent

    @classmethod
    def remove_instance(cls, workspace: Any, project_name: str) -> bool:
        """
        Remove a FilmetoAgent instance from the cache.

        Args:
            workspace: The workspace object
            project_name: The name of the project

        Returns:
            bool: True if instance was removed, False if it didn't exist
        """
        workspace_path = get_workspace_path_safe(workspace)
        instance_key = f"{workspace_path}:{project_name}"

        if instance_key in cls._instances:
            del cls._instances[instance_key]
            logger.info(f"Removed FilmetoAgent instance for {instance_key}")
            return True
        return False

    @classmethod
    def clear_all_instances(cls):
        """Clear all cached FilmetoAgent instances."""
        count = len(cls._instances)
        cls._instances.clear()
        logger.info(f"Cleared {count} FilmetoAgent instance(s)")

    @classmethod
    def list_instances(cls) -> list:
        """
        List all cached instance keys.

        Returns:
            List of instance keys in format "workspace_path:project_name"
        """
        return list(cls._instances.keys())

    @classmethod
    def has_instance(cls, workspace: Any, project_name: str) -> bool:
        """
        Check if an instance exists for the given workspace and project.

        Args:
            workspace: The workspace object
            project_name: The name of the project

        Returns:
            bool: True if instance exists, False otherwise
        """
        workspace_path = get_workspace_path_safe(workspace)
        instance_key = f"{workspace_path}:{project_name}"
        return instance_key in cls._instances
