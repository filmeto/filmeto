"""
Integration test for screenwriter conversation flow.

This test verifies the complete conversation chain:
1. User sends a message requesting screenplay writing
2. Screenwriter crew member processes the request
3. Skill is executed via in-context execution
4. Results are properly returned through the ReAct loop
"""

import asyncio
import json
import os
import sys
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

# Add workspace to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestScreenwriterConversationFlow:
    """Integration tests for the screenwriter conversation flow."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temp directory for test project
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_path = self.temp_dir / "test_film_project"
        self.project_path.mkdir(parents=True, exist_ok=True)
        
        # Create screenwriter crew member config
        self.crew_config_path = self.temp_dir / "screenwriter.md"
        self.crew_config_path.write_text("""---
name: screenwriter
description: A creative screenwriter who develops story beats, dialogue, and character arcs
skills:
  - write_screenplay_outline
  - write_single_scene
model: gpt-4o-mini
temperature: 0.5
max_steps: 5
color: "#32cd32"
icon: "✍️"
---
You are a professional screenwriter with expertise in story structure and character development.
When asked to write scenes or outlines, use your available skills to create the content.
""")

    def teardown_method(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)

    def test_screenwriter_system_prompt_contains_skill_details(self):
        """Test that the screenwriter's system prompt includes skill call instructions."""
        from agent.crew.crew_member import CrewMember
        
        crew_member = CrewMember(
            config_path=str(self.crew_config_path),
            workspace=None,
            project=None
        )
        
        system_prompt = crew_member._build_system_prompt()
        
        # Check that the prompt contains skill information
        assert 'write_screenplay_outline' in system_prompt
        assert 'write_single_scene' in system_prompt
        
        # Check that descriptions are included
        assert 'Description' in system_prompt or 'description' in system_prompt.lower()
        
        # Check that example JSON is included
        assert 'type' in system_prompt
        assert 'execute_skill' in system_prompt
        assert 'prompt' in system_prompt
        
        # Check that action instructions are clear
        assert 'JSON' in system_prompt
        assert 'final' in system_prompt.lower()

    def test_screenwriter_parses_llm_skill_call(self):
        """Test that the screenwriter correctly parses an LLM response that calls a skill."""
        from agent.crew.crew_member import CrewMember
        
        crew_member = CrewMember(
            config_path=str(self.crew_config_path),
            workspace=None,
            project=None
        )
        
        # Simulate an LLM response that wants to call the outline skill
        llm_response = json.dumps({
            "type": "tool",
            "tool_name": "execute_skill",
            "tool_args": {
                "skill_name": "write_screenplay_outline",
                "prompt": "A film noir mystery about a detective investigating corruption. Genre: Film Noir. 8 scenes."
            }
        })
        
        action = crew_member._parse_action(llm_response)
        
        assert action.action_type == "tool"
        assert action.tool_name == "execute_skill"
        assert action.tool_args["skill_name"] == "write_screenplay_outline"
        assert "prompt" in action.tool_args

    def test_screenwriter_skill_execution_creates_scenes(self):
        """Test that executing a skill through the screenwriter creates scenes."""
        from agent.crew.crew_member import CrewMember, CrewMemberAction
        from app.data.screen_play import ScreenPlayManager
        
        # Create screenplay manager
        screenplay_manager = ScreenPlayManager(self.project_path)
        
        # Create mock project
        mock_project = MagicMock()
        mock_project.project_path = str(self.project_path)
        mock_project.screenplay_manager = screenplay_manager
        mock_project.project_name = 'test_film_project'
        
        crew_member = CrewMember(
            config_path=str(self.crew_config_path),
            workspace=None,
            project=mock_project
        )
        
        # Create and execute a skill action
        action = CrewMemberAction(
            action_type='skill',
            skill='write_screenplay_outline',
            args={
                'concept': 'A romantic comedy about two rivals',
                'genre': 'Romance',
                'num_scenes': 4
            }
        )
        
        result = crew_member._execute_skill(action)
        
        # Verify the skill executed successfully
        assert 'Successfully created' in result or 'success' in result.lower()
        
        # Verify scenes were actually created
        scenes = screenplay_manager.list_scenes()
        assert len(scenes) == 4

    def test_screenwriter_single_scene_skill(self):
        """Test executing the write_single_scene skill through the screenwriter."""
        from agent.crew.crew_member import CrewMember, CrewMemberAction
        from app.data.screen_play import ScreenPlayManager
        
        screenplay_manager = ScreenPlayManager(self.project_path)
        
        mock_project = MagicMock()
        mock_project.project_path = str(self.project_path)
        mock_project.screenplay_manager = screenplay_manager
        mock_project.project_name = 'test_film_project'
        
        crew_member = CrewMember(
            config_path=str(self.crew_config_path),
            workspace=None,
            project=mock_project
        )
        
        # Test writing a single scene
        action = CrewMemberAction(
            action_type='skill',
            skill='write_single_scene',
            args={
                'scene_id': 'scene_opening',
                'title': 'The Meeting',
                'content': """# INT. COFFEE SHOP - MORNING

SARAH (30s, professional) sits alone at a corner table, nervously checking her phone.

**SARAH**
*(muttering)*
Where is he?

The door opens. MICHAEL (30s, charming) enters, scanning the room.

**MICHAEL**
*(spots her)*
Sarah?

SARAH stands, extending her hand.

**SARAH**
Michael. Thank you for coming.
""",
                'location': 'COFFEE SHOP',
                'time_of_day': 'MORNING',
                'characters': ['SARAH', 'MICHAEL'],
                'story_beat': 'character_introduction'
            }
        )
        
        result = crew_member._execute_skill(action)
        
        # Verify success
        assert 'success' in result.lower() or 'created' in result.lower()
        
        # Verify the scene was created
        scene = screenplay_manager.get_scene('scene_opening')
        assert scene is not None
        assert scene.title == 'The Meeting'
        assert 'SARAH' in scene.characters
        assert 'MICHAEL' in scene.characters

    def test_screenwriter_skill_with_structured_events(self):
        """Test that skill execution emits proper stream events."""
        from agent.crew.crew_member import CrewMember, CrewMemberAction
        from app.data.screen_play import ScreenPlayManager
        
        screenplay_manager = ScreenPlayManager(self.project_path)
        
        mock_project = MagicMock()
        mock_project.project_path = str(self.project_path)
        mock_project.screenplay_manager = screenplay_manager
        mock_project.project_name = 'test_film_project'
        
        crew_member = CrewMember(
            config_path=str(self.crew_config_path),
            workspace=None,
            project=mock_project
        )
        crew_member._session_id = 'test_session'
        
        # Track emitted events
        events = []
        def track_event(event):
            events.append(event)
        
        action = CrewMemberAction(
            action_type='skill',
            skill='write_single_scene',
            args={
                'scene_id': 'scene_event_test',
                'title': 'Event Test Scene',
                'content': '# INT. TEST - DAY\n\nA test scene.'
            }
        )
        
        result = crew_member._execute_skill_with_structured_content(
            action,
            on_stream_event=track_event,
            message_id='test_msg_001'
        )
        
        # Verify events were emitted
        event_types = [e.event_type for e in events]
        assert 'skill_start' in event_types, f"Expected skill_start event, got: {event_types}"
        assert 'skill_progress' in event_types, f"Expected skill_progress event, got: {event_types}"
        assert 'skill_end' in event_types, f"Expected skill_end event, got: {event_types}"
        
        # Verify start event contains skill info
        start_event = next(e for e in events if e.event_type == 'skill_start')
        assert start_event.data['skill_name'] == 'write_single_scene'
        
        # Verify end event contains result
        end_event = next(e for e in events if e.event_type == 'skill_end')
        assert 'result' in end_event.data

    def test_skill_prompt_includes_required_inputs(self):
        """Test that the skill prompt clearly indicates required inputs."""
        from agent.skill.skill_service import SkillService
        
        skill_service = SkillService(workspace=None)
        
        # Get write_single_scene skill
        skill = skill_service.get_skill('write_single_scene')
        assert skill is not None
        
        # Check that required inputs are documented in knowledge
        knowledge = skill.knowledge
        assert 'Input Requirements' in knowledge
        assert 'scene_id' in knowledge
        assert 'title' in knowledge
        assert 'content' in knowledge

    def test_react_loop_processes_skill_observation(self):
        """Test that the ReAct loop properly handles skill execution observations."""
        from agent.crew.crew_member import CrewMember
        from app.data.screen_play import ScreenPlayManager
        
        screenplay_manager = ScreenPlayManager(self.project_path)
        
        mock_project = MagicMock()
        mock_project.project_path = str(self.project_path)
        mock_project.screenplay_manager = screenplay_manager
        mock_project.project_name = 'test_film_project'
        
        crew_member = CrewMember(
            config_path=str(self.crew_config_path),
            workspace=None,
            project=mock_project
        )
        
        # Verify that the system prompt includes instructions for skill observation handling
        system_prompt = crew_member._build_system_prompt()
        
        # Check that it mentions observations
        assert 'observation' in system_prompt.lower() or 'result' in system_prompt.lower()
        
        # Check that it explains the ReAct flow
        assert 'skill' in system_prompt.lower()
        assert 'final' in system_prompt.lower()


class TestSkillPromptFormatting:
    """Tests for proper skill prompt formatting."""

    def test_skill_example_is_valid_json(self):
        """Test that skill examples are valid JSON."""
        from agent.skill.skill_service import SkillService
        
        skill_service = SkillService(workspace=None)
        
        for skill_name in ['write_screenplay_outline', 'write_single_scene']:
            skill = skill_service.get_skill(skill_name)
            assert skill is not None, f"Skill {skill_name} not found"
            
            example = skill.get_example_call()
            
            # Should be valid JSON
            try:
                parsed = json.loads(example)
                assert 'type' in parsed
                assert parsed['type'] == 'tool'
                assert parsed['tool_name'] == 'execute_skill'
                assert parsed['tool_args']['skill_name'] == skill_name
                assert 'prompt' in parsed['tool_args']
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in example for {skill_name}: {e}")

    def test_detailed_skill_format_includes_name_and_description(self):
        """Test that the detailed skill format includes name and description."""
        from agent.crew.crew_member import _format_skill_entry_detailed
        from agent.skill.skill_service import SkillService
        
        skill_service = SkillService(workspace=None)
        skill = skill_service.get_skill('write_screenplay_outline')
        
        formatted = _format_skill_entry_detailed(skill)
        
        # Check required sections
        assert '###' in formatted  # Has heading
        assert 'Description' in formatted or 'description' in formatted.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
