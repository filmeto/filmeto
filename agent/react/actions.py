"""Action types for ReAct pattern."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class ActionType(str, Enum):
    """Constants for ReAct action types."""
    TOOL = "tool"
    FINAL = "final"
    ERROR = "error"


@dataclass(frozen=True)
class ReactAction(ABC):
    """
    Base class for ReAct actions. Immutable for safety.

    Each action represents a decision made by the LLM during the ReAct loop.
    """
    type: str

    @abstractmethod
    def get_thinking(self) -> Optional[str]:
        """Get the thinking/reasoning for this action."""
        pass

    def is_tool(self) -> bool:
        """Check if this is a tool action."""
        return self.type == ActionType.TOOL.value

    def is_final(self) -> bool:
        """Check if this is a final action."""
        return self.type == ActionType.FINAL.value

    def is_error(self) -> bool:
        """Check if this is an error action."""
        return self.type == ActionType.ERROR.value

    def get_status_for(self) -> str:
        """Get the React status associated with this action."""
        if self.is_tool():
            return "RUNNING"
        elif self.is_final():
            return "FINAL"
        elif self.is_error():
            return "FAILED"
        return "RUNNING"

    def to_event_payload(self, **kwargs) -> Dict[str, Any]:
        """Build event payload for this action. Subclasses can override."""
        payload = {"type": self.type}
        thinking = self.get_thinking()
        if thinking:
            payload["thinking"] = thinking
        payload.update(kwargs)
        return payload

    def get_summary(self) -> str:
        """Get a summary description of this action."""
        if self.is_final():
            return "ReAct process completed"
        elif self.is_error():
            return "ReAct process encountered an error"
        elif self.is_tool():
            return "Executing tool"
        return "Processing action"


@dataclass(frozen=True)
class ToolAction(ReactAction):
    """
    Action that invokes a tool/function.

    Attributes:
        type: Action type (always TOOL)
        tool_name: Name of the tool to invoke
        tool_args: Arguments to pass to the tool
        thinking: The agent's thinking process
    """
    type: str = ActionType.TOOL.value
    tool_name: str = ""
    tool_args: Dict[str, Any] = None
    thinking: Optional[str] = None

    def __post_init__(self):
        if self.tool_args is None:
            object.__setattr__(self, 'tool_args', {})

    def get_thinking(self) -> Optional[str]:
        return self.thinking

    def to_event_payload(self, **kwargs) -> Dict[str, Any]:
        """Build event payload for tool action."""
        payload = super().to_event_payload(**kwargs)
        payload.update({
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
        })
        return payload

    def get_summary(self) -> str:
        """Get summary for tool action."""
        if self.tool_name:
            return f"Executing tool: {self.tool_name}"
        return "Executing tool"

    def to_start_payload(self) -> Dict[str, Any]:
        """Build payload for tool start event."""
        return self.to_event_payload()

    def to_end_payload(self, result: Any = None, ok: bool = True, error: Optional[str] = None) -> Dict[str, Any]:
        """Build payload for tool end event."""
        payload = {
            "tool_name": self.tool_name,
            "ok": ok,
        }
        if ok and result is not None:
            payload["result"] = result
        if not ok and error:
            payload["error"] = error
        return payload

    def to_progress_payload(self, progress: Any) -> Dict[str, Any]:
        """Build payload for tool progress event."""
        return {
            "tool_name": self.tool_name,
            "progress": progress,
        }


@dataclass(frozen=True)
class FinalAction(ReactAction):
    """
    Action that completes the ReAct loop with a final response.

    Attributes:
        type: Action type (always FINAL)
        final: The final response content
        thinking: The agent's thinking process
        stop_reason: Reason for stopping (final_action, max_steps_reached, etc.)
        speak_to: Target recipient name for routing (e.g., 'You' for user, or crew member name)
    """
    type: str = ActionType.FINAL.value
    final: str = ""
    thinking: Optional[str] = None
    stop_reason: str = "final_action"
    speak_to: Optional[str] = None

    def get_thinking(self) -> Optional[str]:
        return self.thinking

    def to_event_payload(self, **kwargs) -> Dict[str, Any]:
        """Build event payload for final action."""
        payload = super().to_event_payload(**kwargs)
        payload.update({
            "final_response": self.final,
            "stop_reason": self.stop_reason,
        })
        if self.speak_to:
            payload["speak_to"] = self.speak_to
        return payload

    def get_summary(self) -> str:
        """Get summary for final action."""
        from .constants import StopReason
        if self.stop_reason == StopReason.MAX_STEPS.value:
            return "ReAct process stopped after reaching maximum steps"
        elif self.stop_reason == StopReason.USER_INTERRUPTED.value:
            return "ReAct process interrupted by user"
        return "ReAct process completed successfully"

    def to_final_payload(self, step: int = 0, max_steps: int = 0) -> Dict[str, Any]:
        """Build payload for final event."""
        payload = {
            "final_response": self.final,
            "stop_reason": self.stop_reason,
            "summary": self.get_summary(),
        }
        if self.speak_to:
            payload["speak_to"] = self.speak_to
        return payload


@dataclass(frozen=True)
class ErrorAction(ReactAction):
    """
    Action representing an error during action parsing or execution.

    Attributes:
        type: Action type (always ERROR)
        error: Error message
        thinking: The agent's thinking process (if available)
        raw_response: The raw LLM response that caused the error
    """
    type: str = ActionType.ERROR.value
    error: str = ""
    thinking: Optional[str] = None
    raw_response: str = ""

    def get_thinking(self) -> Optional[str]:
        return self.thinking

    def to_event_payload(self, **kwargs) -> Dict[str, Any]:
        """Build event payload for error action."""
        payload = super().to_event_payload(**kwargs)
        payload.update({
            "error": self.error,
        })
        if self.raw_response:
            payload["raw_response"] = self.raw_response
        payload.update(kwargs)
        return payload

    def get_summary(self) -> str:
        """Get summary for error action."""
        return f"ReAct process encountered an error: {self.error}"

    def to_error_payload(self, details: Optional[str] = None) -> Dict[str, Any]:
        """Build payload for error event."""
        payload = {
            "error": self.error,
        }
        if details:
            payload["details"] = details
        elif self.raw_response:
            payload["details"] = self.raw_response[:500]
        return payload
