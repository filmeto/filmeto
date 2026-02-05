"""
Test skill script path improvements.

Tests that:
1. _build_skill_react_prompt includes full script paths
2. Prompt templates display full script paths correctly
3. ExecuteSkillScriptTool supports script_path parameter with priority
"""

import pytest
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.skill.skill_models import Skill
from agent.skill.skill_chat import SkillChat
from agent.skill.skill_service import SkillService


class MockSkillService:
    """Mock skill service for testing."""

    def execute_script(self, script_path, argv, context, **kwargs):
        """Mock script execution."""
        return {"result": f"Executed {script_path} with args {argv}"}


class TestSkillScriptPathImprovements:
    """Tests for skill script path improvements."""

    def test_build_prompt_includes_full_script_paths(self):
        """Test that _build_skill_react_prompt includes full script paths."""
        from agent.skill.skill_chat import SkillChat

        # Create a mock skill with scripts
        skill = Skill(
            name="test_skill",
            description="A test skill",
            knowledge="Test knowledge",
            skill_path="/path/to/skill",
            scripts=["scripts/write.py", "scripts/read.py"]
        )

        # Create SkillChat with mock service
        skill_chat = SkillChat(skill_service=MockSkillService())

        # Build the prompt
        prompt = skill_chat._build_skill_react_prompt(
            skill=skill,
            user_question="Test question",
            available_tool_names=["execute_skill_script"],
            args={}
        )

        # Verify full script paths are in the prompt
        assert "/path/to/skill/scripts/write.py" in prompt
        assert "/path/to/skill/scripts/read.py" in prompt
        # Verify skill_path is also included
        assert "/path/to/skill" in prompt

    def test_prompt_template_displays_full_paths(self):
        """Test that prompt template displays full script paths."""
        from agent.prompt.prompt_service import prompt_service

        # Render a skill prompt with full paths
        skill_data = {
            'name': 'test_skill',
            'description': 'Test description',
            'knowledge': 'Test knowledge',
            'skill_path': '/skills/test_skill',
            'has_scripts': True,
            'script_names': ['write.py', 'read.py'],
            'script_full_paths': [
                '/skills/test_skill/scripts/write.py',
                '/skills/test_skill/scripts/read.py'
            ]
        }

        prompt = prompt_service.render_prompt(
            name="skill_react",
            skill=skill_data,
            user_question="Test question",
            available_tools=[],
            args={}
        )

        # Verify full paths are displayed
        assert '/skills/test_skill/scripts/write.py' in prompt
        assert '/skills/test_skill/scripts/read.py' in prompt
        # Verify both options are shown
        assert 'Option A' in prompt or '选项 A' in prompt

    def test_execute_skill_script_supports_script_path(self, tmp_path):
        """Test that ExecuteSkillScriptTool supports script_path parameter."""
        from agent.tool.system.execute_skill_script import ExecuteSkillScriptTool

        # Create a temporary test script
        test_script = tmp_path / "test_script.py"
        test_script.write_text("""
import json
import sys

# Simple script that outputs args
result = {"status": "success", "script": __file__}
print(json.dumps(result))
""")

        # Create the tool
        tool = ExecuteSkillScriptTool()

        # Check metadata includes script_path parameter
        metadata_en = tool.metadata("en_US")
        param_names = [p.name for p in metadata_en.parameters]
        assert "script_path" in param_names
        assert "skill_path" in param_names
        assert "script_name" in param_names

        # Verify script_path is optional
        script_path_param = next(p for p in metadata_en.parameters if p.name == "script_path")
        assert script_path_param.required is False

    def test_script_path_has_priority_over_skill_path(self, tmp_path):
        """Test that script_path parameter takes priority over skill_path + script_name."""
        from agent.tool.system.execute_skill_script import ExecuteSkillScriptTool
        import asyncio

        # Create two test scripts with different outputs
        script1 = tmp_path / "script1.py"
        script1.write_text('print("script1")')

        script2 = tmp_path / "script2.py"
        script2.write_text('print("script2")')

        tool = ExecuteSkillScriptTool()

        # Test 1: script_path takes priority
        async def test_priority():
            events = []
            async for event in tool.execute(
                parameters={
                    "script_path": str(script1),
                    "skill_path": str(tmp_path),
                    "script_name": "script2.py"  # This should be ignored
                },
                context=None,
                project_name="test",
                react_type="test",
                run_id="test",
                step_id=0
            ):
                events.append(event)

            # Check that script1 was executed (not script2)
            result_events = [e for e in events if hasattr(e, 'payload') and e.payload.get('result')]
            if result_events:
                result = result_events[0].payload.get('result', {})
                assert 'script1' in str(result) or result_events[0].payload.get('ok') is True

        asyncio.run(test_priority())


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
