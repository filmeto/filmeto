"""Skill content for Filmeto agent system."""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


class SkillExecutionState(str, Enum):
    """Skill execution states."""
    PENDING = "pending"         # Skill is queued/pending
    IN_PROGRESS = "in_progress"  # Skill is executing
    COMPLETED = "completed"       # Skill completed successfully
    ERROR = "error"              # Skill execution failed


@dataclass
class SkillContent(StructureContent):
    """Skill execution content - tracks skill execution progress and results.

    This content type is used to display skill execution states in the UI,
    merging multiple skill events (start, progress, end, error) into a single
    display item that updates as the skill executes.
    """
    content_type: ContentType = ContentType.SKILL
    # Execution state
    state: SkillExecutionState = SkillExecutionState.PENDING

    # Skill identification
    skill_name: str = ""
    skill_description: str = ""

    # Progress tracking (for in_progress state)
    progress_percentage: Optional[int] = None  # 0-100
    progress_text: str = ""  # Human-readable progress message

    # Result (for completed state)
    result: str = ""  # Final result/output from skill

    # Error (for error state)
    error_message: str = ""  # Error message if execution failed

    # Nested child content (tool calls, etc. during skill execution)
    child_contents: List[Dict[str, Any]] = field(default_factory=list)

    # Run ID for tracking skill execution lifecycle
    run_id: str = ""

    # Legacy metadata fields (for skill description)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    example_call: str = None
    usage_criteria: str = None

    def _get_data(self) -> Dict[str, Any]:
        data = {
            "skill_name": self.skill_name,
            "description": self.skill_description,
            "state": self.state.value if isinstance(self.state, SkillExecutionState) else self.state,
            "run_id": self.run_id,
        }
        # Add progress info if in progress
        if self.state == SkillExecutionState.IN_PROGRESS:
            if self.progress_percentage is not None:
                data["progress_percentage"] = self.progress_percentage
            if self.progress_text:
                data["progress_text"] = self.progress_text
        # Add result if completed
        elif self.state == SkillExecutionState.COMPLETED and self.result:
            data["result"] = self.result
        # Add error if failed
        elif self.state == SkillExecutionState.ERROR and self.error_message:
            data["error_message"] = self.error_message

        # Add child contents if any
        if self.child_contents:
            data["child_contents"] = self.child_contents

        # Legacy fields for skill description
        if self.parameters:
            data["parameters"] = self.parameters
        if self.example_call:
            data["example_call"] = self.example_call
        if self.usage_criteria:
            data["usage_criteria"] = self.usage_criteria
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillContent':
        """Create a SkillContent from a dictionary."""
        data_dict = data.get("data", {})

        # Parse state
        state_value = data_dict.get("state", "pending")
        if isinstance(state_value, str):
            try:
                state = SkillExecutionState(state_value)
            except ValueError:
                state = SkillExecutionState.PENDING
        else:
            state = SkillExecutionState.PENDING

        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            # Execution state fields
            state=state,
            skill_name=data_dict.get("skill_name", ""),
            skill_description=data_dict.get("description", ""),
            progress_percentage=data_dict.get("progress_percentage"),
            progress_text=data_dict.get("progress_text", ""),
            result=data_dict.get("result", ""),
            error_message=data_dict.get("error_message", ""),
            # Child contents and run_id
            child_contents=data_dict.get("child_contents", []),
            run_id=data_dict.get("run_id", ""),
            # Legacy fields
            parameters=data_dict.get("parameters", []),
            example_call=data_dict.get("example_call"),
            usage_criteria=data_dict.get("usage_criteria")
        )
