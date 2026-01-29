from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING, AsyncGenerator
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .tool_context import ToolContext
    from agent.event.agent_event import AgentEvent


@dataclass
class ToolParameter:
    """
    Represents a parameter of a tool.

    Attributes:
        name: Parameter name
        description: Parameter description
        param_type: Parameter type (string, number, boolean, array, object, etc.)
        required: Whether the parameter is required
        default: Default value for the parameter (optional)
    """
    name: str
    description: str
    param_type: str
    required: bool = False
    default: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "name": self.name,
            "description": self.description,
            "type": self.param_type,
            "required": self.required
        }
        if self.default is not None:
            result["default"] = self.default
        return result


@dataclass
class ToolMetadata:
    """
    Metadata information for a tool.

    Attributes:
        name: Tool name
        description: Tool description
        parameters: List of tool parameters
        return_description: Description of the return value
    """
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    return_description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [p.to_dict() for p in self.parameters],
            "return_description": self.return_description
        }


class BaseTool(ABC):
    """
    Abstract base class for all tools.
    All tools must inherit from this class and implement the execute method.
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional["ToolContext"] = None,
        project_name: str = "",
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
    ) -> AsyncGenerator["AgentEvent", None]:
        """
        Execute the tool with given parameters and context.

        This is an async method that yields ReactEvent objects for tracking execution progress.

        Args:
            parameters: Dictionary of parameters for the tool
            context: Optional ToolContext object containing workspace, project_name, etc.
            project_name: Project name for event tracking
            react_type: React type for event tracking
            run_id: Run ID for event tracking
            step_id: Step ID for event tracking
            sender_id: ID of the event sender
            sender_name: Display name of the event sender

        Yields:
            ReactEvent objects with types:
            - "tool_progress" - Progress update during execution
            - "tool_end" - Tool execution completed (with result in payload)
            - "error" - Tool execution failed (with error in payload)
        """
        pass

    def metadata(self, lang: str = "en_US") -> ToolMetadata:
        """
        Get metadata information for the tool.

        Args:
            lang: Language code for localized metadata (e.g., "en_US", "zh_CN")

        Returns:
            ToolMetadata object containing the tool's metadata
        """
        # Default implementation returns basic metadata
        # Subclasses should override this to provide detailed metadata
        return ToolMetadata(
            name=self.name,
            description=self.description,
            parameters=[],
            return_description=""
        )

    def _create_event(
        self,
        event_type: str,
        project_name: str = "",
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
        **kwargs
    ) -> "AgentEvent":
        """
        Create a ReactEvent for tool execution.

        Args:
            event_type: Type of event (tool_progress, tool_end, error)
            project_name: Project name
            react_type: React type
            run_id: Run ID
            step_id: Step ID
            sender_id: ID of the event sender
            sender_name: Display name of the event sender
            **kwargs: Additional event-specific data

        Returns:
            ReactEvent object
        """
        from agent.event.agent_event import AgentEvent

        return AgentEvent.create(
            event_type=event_type,
            project_name=project_name,
            react_type=react_type,
            run_id=run_id,
            step_id=step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            tool_name=self.name,
            **kwargs
        )
