"""
Comprehensive unit tests for the skill execution chain.

Tests the entire flow from skill loading to execution:
1. Skill loading without parameter metadata
2. SkillService in-context execution
3. Crew member skill prompt generation
4. End-to-end skill execution with screenplay manager
"""

import json
import os
import sys
import pytest
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

# Add workspace to path for direct imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSkillLoading:
    """Tests for skill loading and parameter parsing."""

    def setup_method(self):
        """Set up test fixtures."""
        # Import directly to avoid circular imports
        from agent.skill.skill_service import SkillService
        self.skill_service = SkillService(workspace=None)

    def test_skill_service_loads_system_skills(self):
        """Test that SkillService loads system skills correctly."""
        skills = self.skill_service.get_all_skills()
        skill_names = [s.name for s in skills]
        
        assert 'write_screenplay_outline' in skill_names
        assert 'write_single_scene' in skill_names

    def test_skill_has_no_parameter_metadata(self):
        """Test that skills do not expose parameter metadata."""
        skill = self.skill_service.get_skill('write_screenplay_outline')

        assert skill is not None
        assert not hasattr(skill, 'parameters')

    def test_skill_input_requirements_in_knowledge(self):
        """Test that input requirements are described in knowledge."""
        skill = self.skill_service.get_skill('write_screenplay_outline')

        assert skill is not None
        assert 'Input Requirements' in skill.knowledge
        assert 'concept' in skill.knowledge

    def test_skill_example_call_generation(self):
        """Test that skill generates a valid example call JSON."""
        skill = self.skill_service.get_skill('write_screenplay_outline')
        
        example_call = skill.get_example_call()
        
        # Should be valid JSON
        parsed = json.loads(example_call)
        assert parsed['type'] == 'tool'
        assert parsed['tool_name'] == 'execute_skill'
        assert 'tool_args' in parsed
        assert parsed['tool_args']['skill_name'] == 'write_screenplay_outline'
        assert 'prompt' in parsed['tool_args']

    def test_write_single_scene_input_requirements(self):
        """Test write_single_scene skill describes required inputs in knowledge."""
        skill = self.skill_service.get_skill('write_single_scene')

        assert skill is not None
        assert 'Input Requirements' in skill.knowledge
        assert 'scene_id' in skill.knowledge
        assert 'title' in skill.knowledge
        assert 'content' in skill.knowledge


class TestToolContext:
    """Tests for the ToolContext class (now includes SkillContext functionality)."""

    def setup_method(self):
        """Set up test fixtures."""
        from agent.tool.tool_context import ToolContext
        self.ToolContext = ToolContext

        # Create a temp directory for test project
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_path = self.temp_dir / "test_project"
        self.project_path.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)

    def test_tool_context_creation(self):
        """Test creating a ToolContext with project and llm_service."""
        mock_workspace = MagicMock()
        mock_project = MagicMock()
        mock_project.project_path = str(self.project_path)
        mock_llm_service = MagicMock()

        context = self.ToolContext(
            workspace=mock_workspace,
            project=mock_project,
            llm_service=mock_llm_service
        )

        assert context.workspace == mock_workspace
        assert context.project == mock_project
        assert context.llm_service == mock_llm_service
        assert context.get_project_path() == str(self.project_path)

    def test_tool_context_get_screenplay_manager(self):
        """Test that ToolContext can get screenplay_manager from project via convenience method."""
        mock_screenplay_manager = MagicMock()
        mock_project = MagicMock()
        mock_project.screenplay_manager = mock_screenplay_manager
        mock_project.project_path = str(self.project_path)

        context = self.ToolContext(project=mock_project)

        # screenplay_manager is not a direct field
        assert not hasattr(context, 'screenplay_manager') or context.get_screenplay_manager() is None
        # But can be accessed via the convenience method
        assert context.get_screenplay_manager() == mock_screenplay_manager

    def test_tool_context_skill_methods(self):
        """Test skill-related convenience methods on ToolContext."""
        context = self.ToolContext()

        # Test skill-related data access
        context.set("skill_knowledge", "test knowledge")
        context.set("skill_description", "test description")
        context.set("skill_reference", "test reference")
        context.set("skill_examples", "test examples")

        assert context.get_skill_knowledge() == "test knowledge"
        assert context.get_skill_description() == "test description"
        assert context.get_skill_reference() == "test reference"
        assert context.get_skill_examples() == "test examples"


class TestSkillServiceInContextExecution:
    """Tests for SkillService in-context execution."""

    def setup_method(self):
        """Set up test fixtures."""
        from agent.skill.skill_service import SkillService
        
        self.skill_service = SkillService(workspace=None)
        
        # Create a temp directory for test project
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_path = self.temp_dir / "test_project"
        self.project_path.mkdir(parents=True, exist_ok=True)
        
        # Create screen_plays directory
        self.screen_plays_dir = self.project_path / "screen_plays"
        self.screen_plays_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)

    def test_execute_skill_in_context_returns_string(self):
        """Test that execute_skill_in_context returns a string."""
        from app.data.screen_play import ScreenPlayManager

        # Create a real screenplay manager
        screenplay_manager = ScreenPlayManager(self.project_path)

        # Create a mock project
        mock_project = MagicMock()
        mock_project.project_path = str(self.project_path)
        mock_project.screenplay_manager = screenplay_manager

        # Get the skill object first
        skill = self.skill_service.get_skill('write_screenplay_outline')
        assert skill is not None, "Skill 'write_screenplay_outline' should exist"

        result = self.skill_service.execute_skill_in_context(
            skill=skill,
            project=mock_project,
            args={
                'concept': 'A test screenplay about robots',
                'genre': 'Sci-Fi',
                'num_scenes': 3
            }
        )

        assert isinstance(result, str)

    def test_execute_skill_in_context_with_none_skill(self):
        """Test execute_skill_in_context with None skill."""
        import asyncio

        result = asyncio.run(self.skill_service.execute_skill_in_context(
            skill=None,
            args={}
        ))

        assert isinstance(result, str)
        assert 'No skill object was provided' in result

    def test_get_skill_prompt_info(self):
        """Test getting formatted skill information for prompts."""
        prompt_info = self.skill_service.get_skill_prompt_info('write_screenplay_outline')
        
        assert 'write_screenplay_outline' in prompt_info
        assert 'Invocation' in prompt_info
        assert 'prompt' in prompt_info.lower()

    def test_execute_skill_from_knowledge_without_llm(self):
        """Test execute_skill_in_context with a skill that has no scripts (knowledge-based)."""
        import asyncio
        from agent.skill.skill_service import Skill

        # Create a skill with knowledge but no scripts
        knowledge_skill = Skill(
            name='test_knowledge_skill',
            description='A skill that only has knowledge, no scripts',
            knowledge='This skill provides guidance on how to perform a specific task.\n\n'
                     '## Instructions\n'
                     '1. First, analyze the input\n'
                     '2. Then, generate the output based on the analysis',
            skill_path='/fake/path',
            scripts=None  # No scripts
        )

        result = asyncio.run(self.skill_service.execute_skill_in_context(
            skill=knowledge_skill,
            args={'input': 'test input'},
            llm_service=None  # No LLM service, should return knowledge guidance
        ))

        assert isinstance(result, str)
        assert 'guidance' in result.lower() or 'instructions' in result.lower()


class TestCrewMemberSkillIntegration:
    """Tests for crew member skill integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_path = self.temp_dir / "test_project"
        self.project_path.mkdir(parents=True, exist_ok=True)
        
        # Create crew member config
        self.crew_config_path = self.temp_dir / "test_crew.md"
        self.crew_config_path.write_text("""---
name: test_screenwriter
description: A test screenwriter for testing
skills:
  - write_screenplay_outline
  - write_single_scene
model: gpt-4o-mini
temperature: 0.5
max_steps: 3
color: "#32cd32"
icon: "✍️"
---
You are a test screenwriter.
""")

    def teardown_method(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)

    def test_crew_member_loads_skills(self):
        """Test that crew member loads and formats skills correctly."""
        from agent.crew.crew_member import CrewMember
        
        crew_member = CrewMember(
            config_path=str(self.crew_config_path),
            workspace=None,
            project=None
        )
        
        assert 'write_screenplay_outline' in crew_member.config.skills
        assert 'write_single_scene' in crew_member.config.skills

    def test_crew_member_formats_skills_prompt(self):
        """Test that crew member formats skills with input requirements in prompt."""
        from agent.crew.crew_member import CrewMember
        
        crew_member = CrewMember(
            config_path=str(self.crew_config_path),
            workspace=None,
            project=None
        )
        
        skills_prompt = crew_member._format_skills_prompt()
        
        # Check that input requirements are included
        assert 'Input Requirements' in skills_prompt
        assert 'concept' in skills_prompt
        assert 'scene_id' in skills_prompt
        assert 'Example call' in skills_prompt or 'example' in skills_prompt.lower()
        assert 'write_screenplay_outline' in skills_prompt

    def test_crew_member_builds_system_prompt_with_skills(self):
        """Test that the full system prompt includes skill information."""
        from agent.crew.crew_member import CrewMember
        
        crew_member = CrewMember(
            config_path=str(self.crew_config_path),
            workspace=None,
            project=None
        )
        
        system_prompt = crew_member._build_system_prompt()
        
        # Check for key components
        assert 'test_screenwriter' in system_prompt
        assert 'skill' in system_prompt.lower()
        assert 'JSON' in system_prompt

    def test_crew_member_parses_skill_action(self):
        """Test that crew member correctly parses skill action from response."""
        from agent.crew.crew_member import CrewMember
        
        crew_member = CrewMember(
            config_path=str(self.crew_config_path),
            workspace=None,
            project=None
        )
        
        # Simulate LLM response with tool call
        response = json.dumps({
            "type": "tool",
            "tool_name": "execute_skill",
            "tool_args": {
                "skill_name": "write_screenplay_outline",
                "prompt": "A mystery thriller. Genre: Thriller. 5 scenes."
            }
        })
        
        action = crew_member._parse_action(response)
        
        assert action.action_type == 'tool'
        assert action.tool_name == 'execute_skill'
        assert action.tool_args['skill_name'] == 'write_screenplay_outline'
        assert 'prompt' in action.tool_args


class TestWriteScreenplayOutlineSkill:
    """Tests for the write_screenplay_outline skill specifically."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_path = self.temp_dir / "test_project"
        self.project_path.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)

    def test_generate_screenplay_outline_function(self):
        """Test the outline generation function directly."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        from agent.skill.system.write_screenplay_outline.scripts.write_screenplay_outline import (
            generate_screenplay_outline
        )
        
        outline = generate_screenplay_outline(
            concept="A detective investigates mysterious disappearances",
            genre="Film Noir",
            num_scenes=5
        )
        
        assert len(outline) == 5
        assert all('scene_number' in scene for scene in outline)
        assert all('content' in scene for scene in outline)
        assert all('characters' in scene for scene in outline)

    def test_write_scenes_to_manager(self):
        """Test writing scenes to a ScreenPlayManager."""
        from app.data.screen_play import ScreenPlayManager
        from agent.skill.system.write_screenplay_outline.scripts.write_screenplay_outline import (
            generate_screenplay_outline,
            write_scenes_to_manager
        )
        
        # Create a real screenplay manager
        screenplay_manager = ScreenPlayManager(self.project_path)
        
        # Generate outline
        outline = generate_screenplay_outline(
            concept="A test screenplay",
            genre="Drama",
            num_scenes=3
        )
        
        # Write scenes
        result = write_scenes_to_manager(outline, screenplay_manager)
        
        assert result['success'] is True
        assert result['total_scenes'] == 3
        assert len(result['created_scenes']) == 3
        
        # Verify scenes were actually created
        scenes = screenplay_manager.list_scenes()
        assert len(scenes) == 3

    def test_execute_in_context(self):
        """Test the execute_in_context function."""
        from app.data.screen_play import ScreenPlayManager
        from agent.tool.tool_context import ToolContext
        from agent.skill.system.write_screenplay_outline.scripts.write_screenplay_outline import (
            execute_in_context
        )

        # Create screenplay manager
        screenplay_manager = ScreenPlayManager(self.project_path)

        # Create context
        mock_project = MagicMock()
        mock_project.project_path = str(self.project_path)
        mock_project.screenplay_manager = screenplay_manager

        context = ToolContext(project=mock_project)
        
        # Execute skill
        result = execute_in_context(
            context,
            concept="A comedy about office workers",
            genre="Comedy",
            num_scenes=4
        )
        
        assert result['success'] is True
        assert result['total_scenes'] == 4
        assert 'outline_summary' in result


class TestWriteSingleSceneSkill:
    """Tests for the write_single_scene skill specifically."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_path = self.temp_dir / "test_project"
        self.project_path.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)

    def test_write_scene_to_manager(self):
        """Test writing a single scene to a ScreenPlayManager."""
        from app.data.screen_play import ScreenPlayManager
        from agent.skill.system.write_single_scene.scripts.write_single_scene import (
            write_scene_to_manager
        )
        
        screenplay_manager = ScreenPlayManager(self.project_path)
        
        result = write_scene_to_manager(
            screenplay_manager=screenplay_manager,
            scene_id="scene_001",
            title="Opening Scene",
            content="# INT. OFFICE - DAY\n\nThe office is empty.",
            scene_number="1",
            location="OFFICE",
            time_of_day="DAY",
            characters=["JOHN", "MARY"]
        )
        
        assert result['success'] is True
        assert result['action'] == 'created'
        assert result['scene_id'] == 'scene_001'
        
        # Verify scene was created
        scene = screenplay_manager.get_scene('scene_001')
        assert scene is not None
        assert scene.title == 'Opening Scene'

    def test_update_existing_scene(self):
        """Test updating an existing scene."""
        from app.data.screen_play import ScreenPlayManager
        from agent.skill.system.write_single_scene.scripts.write_single_scene import (
            write_scene_to_manager
        )
        
        screenplay_manager = ScreenPlayManager(self.project_path)
        
        # Create initial scene
        write_scene_to_manager(
            screenplay_manager=screenplay_manager,
            scene_id="scene_001",
            title="Original Title",
            content="Original content"
        )
        
        # Update the scene
        result = write_scene_to_manager(
            screenplay_manager=screenplay_manager,
            scene_id="scene_001",
            title="Updated Title",
            content="Updated content",
            status="revised"
        )
        
        assert result['success'] is True
        assert result['action'] == 'updated'
        
        # Verify update
        scene = screenplay_manager.get_scene('scene_001')
        assert scene.title == 'Updated Title'
        assert scene.status == 'revised'

    def test_execute_in_context_creates_scene(self):
        """Test execute_in_context creates a scene properly."""
        from app.data.screen_play import ScreenPlayManager
        from agent.tool.tool_context import ToolContext
        from agent.skill.system.write_single_scene.scripts.write_single_scene import (
            execute_in_context
        )

        screenplay_manager = ScreenPlayManager(self.project_path)

        mock_project = MagicMock()
        mock_project.project_path = str(self.project_path)
        mock_project.screenplay_manager = screenplay_manager

        context = ToolContext(project=mock_project)
        
        result = execute_in_context(
            context,
            scene_id="scene_test_001",
            title="Test Scene",
            content="# INT. TEST - DAY\n\nA test scene.",
            location="TEST",
            characters=["TESTER"]
        )
        
        assert result['success'] is True
        
        # Verify scene exists
        scene = screenplay_manager.get_scene('scene_test_001')
        assert scene is not None


class TestEndToEndSkillExecution:
    """End-to-end tests for skill execution through the full chain."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_path = self.temp_dir / "test_project"
        self.project_path.mkdir(parents=True, exist_ok=True)
        
        # Create crew member config
        self.crew_config_path = self.temp_dir / "screenwriter.md"
        self.crew_config_path.write_text("""---
name: screenwriter
description: A screenwriter for testing
skills:
  - write_screenplay_outline
  - write_single_scene
model: gpt-4o-mini
temperature: 0.5
max_steps: 5
color: "#32cd32"
icon: "✍️"
---
You are a screenwriter.
""")

    def teardown_method(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)

    def test_skill_execution_through_crew_member(self):
        """Test executing a skill through the CrewMember._execute_skill method."""
        from agent.crew.crew_member import CrewMember, CrewMemberAction
        from app.data.screen_play import ScreenPlayManager
        
        # Create a real screenplay manager
        screenplay_manager = ScreenPlayManager(self.project_path)
        
        # Create mock project with screenplay manager
        mock_project = MagicMock()
        mock_project.project_path = str(self.project_path)
        mock_project.screenplay_manager = screenplay_manager
        mock_project.project_name = 'test_project'
        
        # Create crew member
        crew_member = CrewMember(
            config_path=str(self.crew_config_path),
            workspace=None,
            project=mock_project
        )
        
        # Create skill action
        action = CrewMemberAction(
            action_type='skill',
            skill='write_screenplay_outline',
            args={
                'concept': 'A test screenplay',
                'genre': 'Test',
                'num_scenes': 2
            }

        )

        # Execute skill
        import asyncio
        result = asyncio.run(crew_member._execute_skill(action))

        assert 'Successfully created' in result or 'success' in result.lower()

        # Verify scenes were created
        scenes = screenplay_manager.list_scenes()
        assert len(scenes) == 2

    def test_skill_execution_with_structured_content(self):
        """Test skill execution with structured content reporting."""
        from agent.crew.crew_member import CrewMember, CrewMemberAction
        from app.data.screen_play import ScreenPlayManager
        
        screenplay_manager = ScreenPlayManager(self.project_path)
        
        mock_project = MagicMock()
        mock_project.project_path = str(self.project_path)
        mock_project.screenplay_manager = screenplay_manager
        mock_project.project_name = 'test_project'
        
        crew_member = CrewMember(
            config_path=str(self.crew_config_path),
            workspace=None,
            project=mock_project
        )
        
        # Track events
        events = []
        def on_stream_event(event):
            events.append(event)
        
        action = CrewMemberAction(
            action_type='skill',
            skill='write_single_scene',
            args={
                'scene_id': 'scene_structured_test',
                'title': 'Structured Test Scene',
                'content': '# INT. TEST - DAY\n\nStructured content test.'
            }
        )

        import asyncio
        result = asyncio.run(crew_member._execute_skill_with_structured_content(
            action,
            on_stream_event=on_stream_event,
            message_id='test_msg_001'
        ))

        # Check that events were emitted
        event_types = [e.event_type for e in events]
        assert 'skill_start' in event_types
        assert 'skill_progress' in event_types
        assert 'skill_end' in event_types

        # Check result
        assert 'success' in result.lower() or 'created' in result.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
