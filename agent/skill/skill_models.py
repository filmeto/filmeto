"""
Skill Data Models

Defines data classes for skills following the Claude skill specification.

Note: SkillContext has been merged into ToolContext for a unified context interface.
Use agent.tool.tool_context.ToolContext instead.
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
