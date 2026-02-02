"""
Skill Data Models

Defines data classes for skills following the Claude skill specification.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json


@dataclass
class SkillParameter:
    """Represents a parameter for a skill."""
    name: str
    param_type: str
    required: bool = False
    default: Any = None
    description: str = ""


@dataclass
class SkillContext:
    """
    Context object for skill execution.
    Provides access to basic business-agnostic services.

    Note: This context should only contain basic services like workspace,
    project, and llm_service. Business-specific services like screenplay_manager
    should be obtained from the project object when needed.
    """
    workspace: Optional[Any] = None
    project: Optional[Any] = None
    llm_service: Optional[Any] = None
    additional_context: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.additional_context is None:
            self.additional_context = {}

    def get_screenplay_manager(self) -> Optional[Any]:
        """Get the screenplay manager from the project if available.

        This is a convenience method for business-specific code that needs
        access to the screenplay manager. It keeps the business-specific
        logic out of the basic context structure.
        """
        if self.project is not None and hasattr(self.project, 'screenplay_manager'):
            return self.project.screenplay_manager
        return None

    def get_project_path(self) -> Optional[str]:
        """Get the project path from the context."""
        if self.project is not None:
            if hasattr(self.project, 'project_path'):
                return self.project.project_path
        return None

    def get_skill_knowledge(self) -> Optional[str]:
        """Get the skill knowledge from the additional context."""
        if self.additional_context:
            return self.additional_context.get("skill_knowledge")
        return None

    def get_skill_description(self) -> Optional[str]:
        """Get the skill description from the additional context."""
        if self.additional_context:
            return self.additional_context.get("skill_description")
        return None

    def get_skill_reference(self) -> Optional[str]:
        """Get the skill reference from the additional context."""
        if self.additional_context:
            return self.additional_context.get("skill_reference")
        return None

    def get_skill_examples(self) -> Optional[str]:
        """Get the skill examples from the additional context."""
        if self.additional_context:
            return self.additional_context.get("skill_examples")
        return None


@dataclass
class Skill:
    """
    Represents a skill with its metadata and content.
    """
    name: str
    description: str
    knowledge: str  # The detailed description part of SKILL.md
    skill_path: str
    reference: Optional[str] = None
    examples: Optional[str] = None
    scripts: Optional[List[str]] = None
    parameters: List[SkillParameter] = field(default_factory=list)

    def get_parameters_prompt(self) -> str:
        """Generate a prompt description of the skill's parameters."""
        if not self.parameters:
            return "No parameters required."

        lines = ["Parameters:"]
        for param in self.parameters:
            req = "(required)" if param.required else "(optional)"
            default_str = f", default: {param.default}" if param.default is not None else ""
            lines.append(f"  - {param.name} ({param.param_type}) {req}{default_str}: {param.description}")
        return "\n".join(lines)

    def get_example_call(self) -> str:
        """Generate an example JSON call for this skill."""
        args = {}
        for param in self.parameters:
            if param.required:
                if param.param_type == "string":
                    args[param.name] = f"<{param.name}>"
                elif param.param_type == "integer":
                    args[param.name] = 0
                elif param.param_type == "array":
                    args[param.name] = []
                elif param.param_type == "boolean":
                    args[param.name] = True
                else:
                    args[param.name] = f"<{param.name}>"

        return json.dumps({
            "type": "skill",
            "skill": self.name,
            "args": args
        }, indent=2)
