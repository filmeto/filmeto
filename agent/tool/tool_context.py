"""
Tool context module.

Provides the ToolContext class that carries runtime information
for tool execution, such as workspace, project, and services.

Note: This class now includes capabilities previously in SkillContext
for a unified context interface across tools and skills.
"""
from typing import Any, Dict, Optional, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from app.data.workspace import Workspace


class ToolContext:
    """
    Context object that carries runtime information for tool execution.

    This object is passed to tools when they are executed, providing access to:
    - workspace: The Workspace object containing project and workspace info
    - project: The current project object (full business object)
    - project_name: The current project name (string)
    - llm_service: Optional LLM service for AI operations
    - Additional services and runtime data

    Attributes:
        workspace: The Workspace object
        project: The current project object (optional)
        project_name: Name of the current project
        data: Additional context data as key-value pairs
    """

    def __init__(
        self,
        workspace: Optional["Workspace"] = None,
        project: Optional[Any] = None,
        project_name: Optional[str] = None,
        llm_service: Optional[Any] = None,
        **kwargs
    ):
        """
        Initialize a ToolContext.

        Args:
            workspace: The Workspace object
            project: The current project object (contains screenplay_manager, etc.)
            project_name: Name of the current project
            llm_service: Optional LLM service
            **kwargs: Additional context data (e.g., skill_service, skill knowledge)
        """
        self._workspace = workspace
        self._project = project
        self._project_name = project_name
        self._llm_service = llm_service
        self._data: Dict[str, Any] = kwargs

    @property
    def workspace(self) -> Optional["Workspace"]:
        """Get the Workspace object."""
        return self._workspace

    @workspace.setter
    def workspace(self, value: "Workspace"):
        """Set the Workspace object."""
        self._workspace = value

    @property
    def project(self) -> Optional[Any]:
        """Get the project object."""
        return self._project

    @project.setter
    def project(self, value: Any):
        """Set the project object."""
        self._project = value

    @property
    def project_name(self) -> Optional[str]:
        """Get the project name."""
        return self._project_name

    @project_name.setter
    def project_name(self, value: str):
        """Set the project name."""
        self._project_name = value

    @property
    def llm_service(self) -> Optional[Any]:
        """Get the LLM service."""
        return self._llm_service

    @llm_service.setter
    def llm_service(self, value: Any):
        """Set the LLM service."""
        self._llm_service = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the context data.

        Args:
            key: The key to look up
            default: Default value if key is not found

        Returns:
            The value associated with the key, or default if not found
        """
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        """
        Set a value in the context data.

        Args:
            key: The key to set
            value: The value to associate with the key
        """
        self._data[key] = value

    def update(self, data: Dict[str, Any]):
        """
        Update the context data with multiple key-value pairs.

        Args:
            data: Dictionary of key-value pairs to add/update
        """
        self._data.update(data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the context to a dictionary representation.

        Note: The workspace object is included directly in the dict.
        For serialization purposes, consider using workspace_path instead.

        Returns:
            Dictionary containing all context data including workspace, project, and project_name
        """
        result = {
            "workspace": self._workspace,
            "project": self._project,
            "project_name": self._project_name,
            "llm_service": self._llm_service,
        }
        result.update(self._data)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolContext":
        """
        Create a ToolContext from a dictionary.

        Args:
            data: Dictionary containing context data.
                  'workspace' can be either a Workspace object or a string path.

        Returns:
            A new ToolContext instance
        """
        workspace = data.pop("workspace", None)
        project = data.pop("project", None)
        project_name = data.pop("project_name", None)
        llm_service = data.pop("llm_service", None)
        return cls(workspace=workspace, project=project, project_name=project_name, llm_service=llm_service, **data)

    # Convenience methods for skill-related access
    # These methods provide the same interface as the old SkillContext

    def get_screenplay_manager(self) -> Optional[Any]:
        """
        Get the screenplay manager from the project if available.

        This is a convenience method for business-specific code that needs
        access to the screenplay manager. It keeps the business-specific
        logic out of the basic context structure.

        Returns:
            The screenplay manager if available, None otherwise
        """
        if self._project is not None and hasattr(self._project, 'screenplay_manager'):
            return self._project.screenplay_manager
        return None

    def get_project_path(self) -> Optional[str]:
        """
        Get the project path from the context.

        Returns:
            The project path if available, None otherwise
        """
        if self._project is not None:
            if hasattr(self._project, 'project_path'):
                return self._project.project_path
        return self._project_name

    def get_skill_knowledge(self) -> Optional[str]:
        """
        Get the skill knowledge from the context data.

        Returns:
            The skill knowledge if available, None otherwise
        """
        return self._data.get("skill_knowledge")

    def get_skill_description(self) -> Optional[str]:
        """
        Get the skill description from the context data.

        Returns:
            The skill description if available, None otherwise
        """
        return self._data.get("skill_description")

    def get_skill_reference(self) -> Optional[str]:
        """
        Get the skill reference from the context data.

        Returns:
            The skill reference if available, None otherwise
        """
        return self._data.get("skill_reference")

    def get_skill_examples(self) -> Optional[str]:
        """
        Get the skill examples from the context data.

        Returns:
            The skill examples if available, None otherwise
        """
        return self._data.get("skill_examples")

    def __repr__(self) -> str:
        """String representation of the context."""
        workspace_repr = (
            f"Workspace(path={self._workspace.workspace_path if self._workspace else None})"
            if self._workspace else None
        )
        return (
            f"ToolContext(workspace={workspace_repr}, "
            f"project_name={self._project_name!r}, "
            f"data={self._data!r})"
        )
