"""Event types for ReAct pattern."""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Set


class AgentEventType(str, Enum):
    """Constants for ReAct event types."""
    LLM_THINKING = "llm_thinking"
    TOOL_START = "tool_start"
    TOOL_PROGRESS = "tool_progress"
    TOOL_END = "tool_end"
    LLM_OUTPUT = "llm_output"
    FINAL = "final"
    ERROR = "error"
    USER_MESSAGE = "user_message"
    PAUSE = "pause"
    RESUME = "resume"
    STATUS_CHANGE = "status_change"
    TODO_UPDATE = "todo_update"

    @classmethod
    def is_tool_event(cls, event_type: str) -> bool:
        """Check if event type is tool-related."""
        return event_type in {cls.TOOL_START.value, cls.TOOL_PROGRESS.value, cls.TOOL_END.value}

    @classmethod
    def is_terminal_event(cls, event_type: str) -> bool:
        """Check if event type indicates termination."""
        return event_type in {cls.FINAL.value, cls.ERROR.value}

    @classmethod
    def get_valid_types(cls) -> Set[str]:
        """Get all valid event type values."""
        return {e.value for e in cls}


@dataclass
class AgentEvent:
    """
    Represents an event in the ReAct process.

    Attributes:
        event_type: Type of event (llm_thinking, tool_start, tool_progress, tool_end, llm_output, final, error)
        project_name: Name of the project
        react_type: Type of ReAct process
        run_id: Unique identifier for the current run
        step_id: Step number in the current run
        sender_id: ID of the event sender (e.g., crew member name, agent name)
        sender_name: Display name of the event sender
        payload: Event-specific data (must be JSON serializable)
    """
    event_type: str
    project_name: str
    react_type: str
    run_id: str
    step_id: int
    sender_id: str = ""
    sender_name: str = ""
    payload: Dict[str, Any] = None

    def __post_init__(self):
        """Validate event fields."""
        # Handle default value for payload
        if self.payload is None:
            self.payload = {}

        # Validate event_type
        valid_types = AgentEventType.get_valid_types()
        if self.event_type not in valid_types:
            raise ValueError(
                f"Invalid event_type: '{self.event_type}'. "
                f"Must be one of: {sorted(valid_types)}"
            )

        # Validate step_id
        if self.step_id < 0:
            raise ValueError(f"step_id must be >= 0, got {self.step_id}")

        # Validate payload is a dict
        if not isinstance(self.payload, dict):
            raise ValueError(f"payload must be a dict, got {type(self.payload).__name__}")

    @staticmethod
    def create(
        event_type: str,
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int,
        sender_id: str = "",
        sender_name: str = "",
        **payload_kwargs
    ) -> "AgentEvent":
        """
        Create an AgentEvent with the given parameters.

        Args:
            event_type: Type of event (from AgentEventType)
            project_name: Name of the project
            react_type: Type of ReAct process
            run_id: Unique identifier for the current run
            step_id: Step number in the current run
            sender_id: ID of the event sender (e.g., crew member name, agent name)
            sender_name: Display name of the event sender
            **payload_kwargs: Event-specific data for the payload

        Returns:
            AgentEvent object

        Example:
            event = AgentEvent.create(
                AgentEventType.TOOL_START.value,
                project_name="my_project",
                react_type="crew",
                run_id="run_123",
                step_id=1,
                sender_id="script_writer",
                sender_name="Script Writer",
                tool_name="my_tool",
                parameters={"arg": "value"}
            )
        """
        return AgentEvent(
            event_type=event_type,
            project_name=project_name,
            react_type=react_type,
            run_id=run_id,
            step_id=step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            payload=payload_kwargs
        )

    @staticmethod
    def error(
        error_message: str,
        project_name: str,
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
        **details
    ) -> "AgentEvent":
        """
        Create an error event.

        Args:
            error_message: The error message
            project_name: Name of the project
            react_type: Type of ReAct process
            run_id: Unique identifier for the current run
            step_id: Step number in the current run
            sender_id: ID of the event sender
            sender_name: Display name of the event sender
            **details: Additional error details

        Returns:
            AgentEvent with type ERROR
        """
        return AgentEvent.create(
            AgentEventType.ERROR.value,
            project_name=project_name,
            react_type=react_type,
            run_id=run_id,
            step_id=step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            error=error_message,
            **details
        )

    @staticmethod
    def final(
        final_response: str,
        project_name: str,
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
        **details
    ) -> "AgentEvent":
        """
        Create a final response event.

        Args:
            final_response: The final response content
            project_name: Name of the project
            react_type: Type of ReAct process
            run_id: Unique identifier for the current run
            step_id: Step number in the current run
            sender_id: ID of the event sender
            sender_name: Display name of the event sender
            **details: Additional details

        Returns:
            AgentEvent with type FINAL
        """
        return AgentEvent.create(
            AgentEventType.FINAL.value,
            project_name=project_name,
            react_type=react_type,
            run_id=run_id,
            step_id=step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            final_response=final_response,
            **details
        )

    @staticmethod
    def tool_start(
        tool_name: str,
        project_name: str,
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
        **details
    ) -> "AgentEvent":
        """
        Create a tool start event.

        Args:
            tool_name: Name of the tool being started
            project_name: Name of the project
            react_type: Type of ReAct process
            run_id: Unique identifier for the current run
            step_id: Step number in the current run
            sender_id: ID of the event sender
            sender_name: Display name of the event sender
            **details: Additional details (e.g., parameters)

        Returns:
            AgentEvent with type TOOL_START
        """
        return AgentEvent.create(
            AgentEventType.TOOL_START.value,
            project_name=project_name,
            react_type=react_type,
            run_id=run_id,
            step_id=step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            tool_name=tool_name,
            **details
        )

    @staticmethod
    def tool_progress(
        tool_name: str,
        progress: str,
        project_name: str,
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
        **details
    ) -> "AgentEvent":
        """
        Create a tool progress event.

        Args:
            tool_name: Name of the tool
            progress: Progress message
            project_name: Name of the project
            react_type: Type of ReAct process
            run_id: Unique identifier for the current run
            step_id: Step number in the current run
            sender_id: ID of the event sender
            sender_name: Display name of the event sender
            **details: Additional details

        Returns:
            AgentEvent with type TOOL_PROGRESS
        """
        return AgentEvent.create(
            AgentEventType.TOOL_PROGRESS.value,
            project_name=project_name,
            react_type=react_type,
            run_id=run_id,
            step_id=step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            tool_name=tool_name,
            progress=progress,
            **details
        )

    @staticmethod
    def tool_end(
        tool_name: str,
        result: Any = None,
        ok: bool = True,
        project_name: str = "",
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
        **details
    ) -> "AgentEvent":
        """
        Create a tool end event.

        Args:
            tool_name: Name of the tool
            result: Tool execution result
            ok: Whether execution succeeded
            project_name: Name of the project
            react_type: Type of ReAct process
            run_id: Unique identifier for the current run
            step_id: Step number in the current run
            sender_id: ID of the event sender
            sender_name: Display name of the event sender
            **details: Additional details

        Returns:
            AgentEvent with type TOOL_END
        """
        payload = {
            "tool_name": tool_name,
            "ok": ok,
            **details
        }
        if result is not None:
            payload["result"] = result
        return AgentEvent.create(
            AgentEventType.TOOL_END.value,
            project_name=project_name,
            react_type=react_type,
            run_id=run_id,
            step_id=step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            **payload
        )
