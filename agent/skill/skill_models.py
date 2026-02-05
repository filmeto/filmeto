"""
Skill Data Models

Defines data classes for skills following the Claude skill specification.

Note: SkillContext has been merged into ToolContext for a unified context interface.
Use agent.tool.tool_context.ToolContext instead.
"""
from dataclasses import dataclass
from typing import List, Optional
import json


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

    def get_example_call(self, prompt: Optional[str] = None) -> str:
        """Generate an example tool call for executing this skill."""
        example_prompt = prompt or f"Describe the task for {self.name} with all required details."
        return json.dumps(
            {
                "type": "tool",
                "tool_name": "execute_skill",
                "tool_args": {
                    "skill_name": self.name,
                    "prompt": example_prompt,
                },
            },
            indent=2,
        )
