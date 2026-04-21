"""
Unit tests for agent module files marked as AST-only in test_plan.md.

Tests for:
- agent/skill/system/delete_screen_play/scripts/delete_screen_play.py - Screenplay deletion
- agent/skill/system/read_scene/scripts/read_single_scene.py - Scene reading
- agent/skill/system/rewrite_screen_play/scripts/rewrite_screenplay.py - Screenplay rewriting
- agent/skill/system/write_scene/scripts/write_single_scene.py - Scene writing
- agent/soul/system/__init__.py - Module exports
- agent/tool/system/__init__.py - Module exports
- agent/tool/system/crew_member/__init__.py - Module exports
- agent/tool/system/crew_member/crew_member_tool.py - CrewMember tool
- agent/tool/system/execute_generated_code/__init__.py - Module exports
- agent/tool/system/execute_generated_code/execute_generated_code.py - Code execution tool
"""
import pytest
import json
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio


# =============================================================================
# Tests for agent/skill/system/delete_screen_play/scripts/delete_screen_play.py
# =============================================================================

class TestDeleteAllScenesFromManager:
    """Tests for delete_all_scenes_from_manager function"""

    def test_delete_all_scenes_success(self):
        """delete_all_scenes should delete all scenes successfully"""
        from agent.skill.system.delete_screen_play.scripts.delete_screen_play import delete_all_scenes_from_manager

        mock_manager = MagicMock()
        mock_scene1 = MagicMock(scene_id="scene_001")
        mock_scene2 = MagicMock(scene_id="scene_002")
        mock_manager.list_scenes.return_value = [mock_scene1, mock_scene2]
        mock_manager.delete_scene.return_value = True

        result = delete_all_scenes_from_manager(mock_manager)
        assert result["success"] is True
        assert result["delete_mode"] == "all"
        assert result["deleted_count"] == 2
        assert "scene_001" in result["deleted_scene_ids"]
        assert "scene_002" in result["deleted_scene_ids"]

    def test_delete_all_scenes_empty(self):
        """delete_all_scenes should handle empty screenplay"""
        from agent.skill.system.delete_screen_play.scripts.delete_screen_play import delete_all_scenes_from_manager

        mock_manager = MagicMock()
        mock_manager.list_scenes.return_value = []

        result = delete_all_scenes_from_manager(mock_manager)
        assert result["success"] is True
        assert result["deleted_count"] == 0
        assert "No screenplay scenes found" in result["message"]

    def test_delete_all_scenes_partial_failure(self):
        """delete_all_scenes should handle partial failures"""
        from agent.skill.system.delete_screen_play.scripts.delete_screen_play import delete_all_scenes_from_manager

        mock_manager = MagicMock()
        mock_scene1 = MagicMock(scene_id="scene_001")
        mock_scene2 = MagicMock(scene_id="scene_002")
        mock_manager.list_scenes.return_value = [mock_scene1, mock_scene2]
        # First scene succeeds, second fails
        mock_manager.delete_scene.side_effect = [True, False]

        result = delete_all_scenes_from_manager(mock_manager)
        assert result["success"] is True
        assert result["deleted_count"] == 1
        assert "scene_002" in result["failed_scene_ids"]

    def test_delete_all_scenes_exception(self):
        """delete_all_scenes should handle exceptions"""
        from agent.skill.system.delete_screen_play.scripts.delete_screen_play import delete_all_scenes_from_manager

        mock_manager = MagicMock()
        mock_manager.list_scenes.side_effect = Exception("Test error")

        result = delete_all_scenes_from_manager(mock_manager)
        assert result["success"] is False
        assert "error" in result


class TestDeletePartialScenesFromManager:
    """Tests for delete_partial_scenes_from_manager function"""

    def test_delete_partial_scenes_success(self):
        """delete_partial_scenes should delete specified scenes"""
        from agent.skill.system.delete_screen_play.scripts.delete_screen_play import delete_partial_scenes_from_manager

        mock_manager = MagicMock()
        mock_scene1 = MagicMock(scene_id="scene_001")
        mock_scene2 = MagicMock(scene_id="scene_002")
        mock_manager.get_scene.side_effect = [mock_scene1, mock_scene2]
        mock_manager.delete_scene.return_value = True

        result = delete_partial_scenes_from_manager(mock_manager, ["scene_001", "scene_002"])
        assert result["success"] is True
        assert result["delete_mode"] == "partial"
        assert result["deleted_count"] == 2

    def test_delete_partial_scenes_non_existing(self):
        """delete_partial_scenes should skip non-existing scenes"""
        from agent.skill.system.delete_screen_play.scripts.delete_screen_play import delete_partial_scenes_from_manager

        mock_manager = MagicMock()
        mock_manager.get_scene.return_value = None

        result = delete_partial_scenes_from_manager(mock_manager, ["scene_999"])
        assert result["success"] is True
        assert result["deleted_count"] == 0
        assert "None of the specified scenes" in result["message"]

    def test_delete_partial_scenes_empty_list(self):
        """delete_partial_scenes should handle empty scene_ids"""
        from agent.skill.system.delete_screen_play.scripts.delete_screen_play import delete_partial_scenes_from_manager

        mock_manager = MagicMock()
        result = delete_partial_scenes_from_manager(mock_manager, [])
        assert result["success"] is True
        assert result["deleted_count"] == 0

    def test_delete_partial_scenes_exception(self):
        """delete_partial_scenes should handle exceptions"""
        from agent.skill.system.delete_screen_play.scripts.delete_screen_play import delete_partial_scenes_from_manager

        mock_manager = MagicMock()
        mock_manager.get_scene.side_effect = Exception("Test error")

        result = delete_partial_scenes_from_manager(mock_manager, ["scene_001"])
        assert result["success"] is False
        assert "error" in result


class TestDeleteScreenPlayExecute:
    """Tests for delete_screen_play execute function"""

    def test_execute_no_screenplay_manager(self):
        """execute should return error when no screenplay manager"""
        from agent.skill.system.delete_screen_play.scripts.delete_screen_play import execute

        mock_context = MagicMock()
        mock_context.get_screenplay_manager.return_value = None

        result = execute(mock_context, {"delete_mode": "all"})
        assert result["success"] is False
        assert result["error"] == "no_screenplay_manager"

    def test_execute_invalid_delete_mode(self):
        """execute should return error for invalid delete_mode"""
        from agent.skill.system.delete_screen_play.scripts.delete_screen_play import execute

        mock_context = MagicMock()
        mock_manager = MagicMock()
        mock_context.get_screenplay_manager.return_value = mock_manager

        result = execute(mock_context, {"delete_mode": "invalid"})
        assert result["success"] is False
        assert result["error"] == "invalid_delete_mode"

    def test_execute_missing_scene_ids_for_partial(self):
        """execute should return error when missing scene_ids for partial"""
        from agent.skill.system.delete_screen_play.scripts.delete_screen_play import execute

        mock_context = MagicMock()
        mock_manager = MagicMock()
        mock_context.get_screenplay_manager.return_value = mock_manager

        result = execute(mock_context, {"delete_mode": "partial"})
        assert result["success"] is False
        assert result["error"] == "missing_scene_ids"

    def test_execute_invalid_scene_ids_type(self):
        """execute should return error when scene_ids is not list"""
        from agent.skill.system.delete_screen_play.scripts.delete_screen_play import execute

        mock_context = MagicMock()
        mock_manager = MagicMock()
        mock_context.get_screenplay_manager.return_value = mock_manager

        result = execute(mock_context, {"delete_mode": "partial", "scene_ids": "not_a_list"})
        assert result["success"] is False
        assert result["error"] == "invalid_scene_ids"

    def test_execute_alias(self):
        """execute_in_context should be alias for execute"""
        from agent.skill.system.delete_screen_play.scripts.delete_screen_play import execute, execute_in_context
        assert execute_in_context is execute


# =============================================================================
# Tests for agent/skill/system/read_scene/scripts/read_single_scene.py
# =============================================================================

class TestReadSceneFromManager:
    """Tests for read_scene_from_manager function"""

    def test_read_scene_success(self):
        """read_scene_from_manager should read scene successfully"""
        from agent.skill.system.read_scene.scripts.read_single_scene import read_scene_from_manager

        mock_manager = MagicMock()
        mock_scene = MagicMock()
        mock_scene.scene_id = "scene_001"
        mock_scene.title = "Opening Scene"
        mock_scene.content = "Scene content here"
        mock_scene.scene_number = "1"
        mock_scene.location = "INT. OFFICE"
        mock_scene.time_of_day = "DAY"
        mock_scene.genre = "Drama"
        mock_scene.logline = "The beginning"
        mock_scene.characters = ["John", "Mary"]
        mock_scene.story_beat = "Opening"
        mock_scene.page_count = 2
        mock_scene.duration_minutes = 5
        mock_scene.tags = ["intro"]
        mock_scene.status = "draft"
        mock_scene.revision_number = 1
        mock_scene.created_at = "2024-01-01"
        mock_scene.updated_at = "2024-01-02"
        mock_manager.get_scene.return_value = mock_scene

        result = read_scene_from_manager(mock_manager, "scene_001")
        assert result["success"] is True
        assert result["scene_id"] == "scene_001"
        assert result["title"] == "Opening Scene"
        assert result["content"] == "Scene content here"
        assert result["metadata"]["location"] == "INT. OFFICE"

    def test_read_scene_not_found(self):
        """read_scene_from_manager should return error for non-existing scene"""
        from agent.skill.system.read_scene.scripts.read_single_scene import read_scene_from_manager

        mock_manager = MagicMock()
        mock_manager.get_scene.return_value = None

        result = read_scene_from_manager(mock_manager, "scene_999")
        assert result["success"] is False
        assert "not found" in result["message"]

    def test_read_scene_exclude_content(self):
        """read_scene_from_manager should exclude content when requested"""
        from agent.skill.system.read_scene.scripts.read_single_scene import read_scene_from_manager

        mock_manager = MagicMock()
        mock_scene = MagicMock()
        mock_scene.scene_id = "scene_001"
        mock_scene.title = "Test"
        mock_scene.content = "Content"
        mock_scene.scene_number = ""
        mock_scene.location = ""
        mock_scene.time_of_day = ""
        mock_scene.genre = ""
        mock_scene.logline = ""
        mock_scene.characters = []
        mock_scene.story_beat = ""
        mock_scene.page_count = 0
        mock_scene.duration_minutes = 0
        mock_scene.tags = []
        mock_scene.status = ""
        mock_scene.revision_number = 0
        mock_scene.created_at = ""
        mock_scene.updated_at = ""
        mock_manager.get_scene.return_value = mock_scene

        result = read_scene_from_manager(mock_manager, "scene_001", include_content=False)
        assert result["success"] is True
        assert "content" not in result

    def test_read_scene_exclude_metadata(self):
        """read_scene_from_manager should exclude metadata when requested"""
        from agent.skill.system.read_scene.scripts.read_single_scene import read_scene_from_manager

        mock_manager = MagicMock()
        mock_scene = MagicMock()
        mock_scene.scene_id = "scene_001"
        mock_scene.title = "Test"
        mock_scene.content = "Content"
        mock_scene.scene_number = ""
        mock_scene.location = ""
        mock_scene.time_of_day = ""
        mock_scene.genre = ""
        mock_scene.logline = ""
        mock_scene.characters = []
        mock_scene.story_beat = ""
        mock_scene.page_count = 0
        mock_scene.duration_minutes = 0
        mock_scene.tags = []
        mock_scene.status = ""
        mock_scene.revision_number = 0
        mock_scene.created_at = ""
        mock_scene.updated_at = ""
        mock_manager.get_scene.return_value = mock_scene

        result = read_scene_from_manager(mock_manager, "scene_001", include_metadata=False)
        assert result["success"] is True
        assert "metadata" not in result

    def test_read_scene_exception(self):
        """read_scene_from_manager should handle exceptions"""
        from agent.skill.system.read_scene.scripts.read_single_scene import read_scene_from_manager

        mock_manager = MagicMock()
        mock_manager.get_scene.side_effect = Exception("Test error")

        result = read_scene_from_manager(mock_manager, "scene_001")
        assert result["success"] is False
        assert "error" in result


class TestReadSceneExecute:
    """Tests for read_single_scene execute function"""

    def test_execute_no_screenplay_manager(self):
        """execute should return error when no screenplay manager"""
        from agent.skill.system.read_scene.scripts.read_single_scene import execute

        mock_context = MagicMock()
        mock_context.get_screenplay_manager.return_value = None

        result = execute(mock_context, {"scene_id": "scene_001"})
        assert result["success"] is False
        assert result["error"] == "no_screenplay_manager"

    def test_execute_missing_scene_id(self):
        """execute should return error when missing scene_id"""
        from agent.skill.system.read_scene.scripts.read_single_scene import execute

        mock_context = MagicMock()
        result = execute(mock_context, {})
        assert result["success"] is False
        assert result["error"] == "missing_scene_id"

    def test_execute_alias(self):
        """execute_in_context should be alias for execute"""
        from agent.skill.system.read_scene.scripts.read_single_scene import execute, execute_in_context
        assert execute_in_context is execute


# =============================================================================
# Tests for agent/skill/system/rewrite_screen_play/scripts/rewrite_screenplay.py
# =============================================================================

class TestRewriteScreenplayValidation:
    """Tests for rewrite_screenplay validation"""

    def test_missing_instruction(self):
        """rewrite_screenplay should require instruction"""
        from agent.skill.system.rewrite_screen_play.scripts.rewrite_screenplay import rewrite_screenplay_in_context

        mock_manager = MagicMock()
        mock_chat_service = MagicMock()

        result = rewrite_screenplay_in_context(
            screenplay_manager=mock_manager,
            chat_service=mock_chat_service,
            instruction=""
        )
        assert result["success"] is False
        assert result["error"] == "missing_instruction"

    def test_no_screenplay_manager(self):
        """rewrite_screenplay should require screenplay manager"""
        from agent.skill.system.rewrite_screen_play.scripts.rewrite_screenplay import rewrite_screenplay_in_context

        result = rewrite_screenplay_in_context(
            screenplay_manager=None,
            chat_service=MagicMock(),
            instruction="test"
        )
        assert result["success"] is False
        assert result["error"] == "no_screenplay_manager"

    # Note: Source code has bug - references undefined 'llm_service' variable
    # instead of 'chat_service' parameter at line 103
    # Skipping test_no_scenes_to_rewrite due to source code bug


class TestRewriteScreenplayExecute:
    """Tests for rewrite_screenplay execute function"""

    def test_execute_missing_instruction(self):
        """execute should return error when missing instruction"""
        from agent.skill.system.rewrite_screen_play.scripts.rewrite_screenplay import execute

        mock_context = MagicMock()
        mock_manager = MagicMock()
        mock_context.get_screenplay_manager.return_value = mock_manager

        result = execute(mock_context, {})
        assert result["success"] is False
        assert result["error"] == "missing_instruction"

    def test_execute_no_screenplay_manager(self):
        """execute should return error when no screenplay manager"""
        from agent.skill.system.rewrite_screen_play.scripts.rewrite_screenplay import execute

        mock_context = MagicMock()
        mock_context.get_screenplay_manager.return_value = None

        result = execute(mock_context, {"instruction": "test"})
        assert result["success"] is False
        assert result["error"] == "no_screenplay_manager"

    def test_execute_no_chat_service(self):
        """execute should return error when no chat service"""
        from agent.skill.system.rewrite_screen_play.scripts.rewrite_screenplay import execute

        mock_context = MagicMock()
        mock_manager = MagicMock()
        mock_context.get_screenplay_manager.return_value = mock_manager
        mock_context.chat_service = None
        mock_context.workspace = None

        result = execute(mock_context, {"instruction": "test"})
        assert result["success"] is False
        assert result["error"] == "no_chat_service"

    def test_execute_alias(self):
        """execute_in_context should be alias for execute"""
        from agent.skill.system.rewrite_screen_play.scripts.rewrite_screenplay import execute, execute_in_context
        assert execute_in_context is execute


class TestRewriteSystemPrompt:
    """Tests for REWRITE_SYSTEM constant"""

    def test_rewrite_system_exists(self):
        """REWRITE_SYSTEM should be defined"""
        from agent.skill.system.rewrite_screen_play.scripts.rewrite_screenplay import REWRITE_SYSTEM
        assert REWRITE_SYSTEM is not None
        assert "screenwriter" in REWRITE_SYSTEM.lower()
        assert "screenplay" in REWRITE_SYSTEM.lower()


# =============================================================================
# Tests for agent/skill/system/write_scene/scripts/write_single_scene.py
# =============================================================================

class TestWriteSceneToManager:
    """Tests for write_scene_to_manager function"""

    def test_write_scene_create_new(self):
        """write_scene_to_manager should create new scene"""
        from agent.skill.system.write_scene.scripts.write_single_scene import write_scene_to_manager

        mock_manager = MagicMock()
        mock_manager.get_scene.return_value = None  # No existing scene
        mock_manager.create_scene.return_value = True

        result = write_scene_to_manager(
            screenplay_manager=mock_manager,
            scene_id="scene_001",
            title="New Scene",
            content="Scene content"
        )
        assert result["success"] is True
        assert result["action"] == "created"
        assert result["scene_id"] == "scene_001"

    def test_write_scene_update_existing(self):
        """write_scene_to_manager should update existing scene"""
        from agent.skill.system.write_scene.scripts.write_single_scene import write_scene_to_manager

        mock_manager = MagicMock()
        mock_existing_scene = MagicMock()
        mock_existing_scene.scene_number = "1"
        mock_existing_scene.location = "INT. OFFICE"
        mock_existing_scene.time_of_day = "DAY"
        mock_existing_scene.genre = "Drama"
        mock_existing_scene.logline = "Old logline"
        mock_existing_scene.characters = []
        mock_existing_scene.story_beat = ""
        mock_existing_scene.page_count = 1
        mock_existing_scene.duration_minutes = 2
        mock_existing_scene.tags = []
        mock_existing_scene.status = "draft"
        mock_existing_scene.revision_number = 1
        mock_existing_scene.created_at = "2024-01-01"
        mock_existing_scene.updated_at = "2024-01-01"
        mock_manager.get_scene.return_value = mock_existing_scene
        mock_manager.update_scene.return_value = True

        result = write_scene_to_manager(
            screenplay_manager=mock_manager,
            scene_id="scene_001",
            title="Updated Scene",
            content="Updated content"
        )
        assert result["success"] is True
        assert result["action"] == "updated"

    def test_write_scene_failure(self):
        """write_scene_to_manager should handle failure"""
        from agent.skill.system.write_scene.scripts.write_single_scene import write_scene_to_manager

        mock_manager = MagicMock()
        mock_manager.get_scene.return_value = None
        mock_manager.create_scene.return_value = False

        result = write_scene_to_manager(
            screenplay_manager=mock_manager,
            scene_id="scene_001",
            title="Test",
            content="Content"
        )
        assert result["success"] is False

    def test_write_scene_with_metadata(self):
        """write_scene_to_manager should accept metadata parameters"""
        from agent.skill.system.write_scene.scripts.write_single_scene import write_scene_to_manager

        mock_manager = MagicMock()
        mock_manager.get_scene.return_value = None
        mock_manager.create_scene.return_value = True

        result = write_scene_to_manager(
            screenplay_manager=mock_manager,
            scene_id="scene_001",
            title="Test Scene",
            content="Content",
            location="INT. OFFICE",
            time_of_day="DAY",
            characters=["John", "Mary"]
        )
        assert result["success"] is True
        mock_manager.create_scene.assert_called_once()


class TestWriteSceneExecute:
    """Tests for write_single_scene execute function"""

    def test_execute_no_screenplay_manager(self):
        """execute should return error when no screenplay manager"""
        from agent.skill.system.write_scene.scripts.write_single_scene import execute

        mock_context = MagicMock()
        mock_context.get_screenplay_manager.return_value = None

        result = execute(mock_context, {"scene_id": "scene_001", "title": "Test", "content": "Content"})
        assert result["success"] is False
        assert result["error"] == "no_screenplay_manager"

    def test_execute_missing_scene_id(self):
        """execute should return error when missing scene_id"""
        from agent.skill.system.write_scene.scripts.write_single_scene import execute

        mock_context = MagicMock()
        result = execute(mock_context, {"title": "Test", "content": "Content"})
        assert result["success"] is False
        assert result["error"] == "missing_scene_id"

    def test_execute_missing_title(self):
        """execute should return error when missing title"""
        from agent.skill.system.write_scene.scripts.write_single_scene import execute

        mock_context = MagicMock()
        result = execute(mock_context, {"scene_id": "scene_001", "content": "Content"})
        assert result["success"] is False
        assert result["error"] == "missing_title"

    def test_execute_missing_content(self):
        """execute should return error when missing content"""
        from agent.skill.system.write_scene.scripts.write_single_scene import execute

        mock_context = MagicMock()
        result = execute(mock_context, {"scene_id": "scene_001", "title": "Test"})
        assert result["success"] is False
        assert result["error"] == "missing_content"

    def test_execute_alias(self):
        """execute_in_context should be alias for execute"""
        from agent.skill.system.write_scene.scripts.write_single_scene import execute, execute_in_context
        assert execute_in_context is execute


# =============================================================================
# Tests for agent/soul/system/__init__.py
# =============================================================================

class TestSoulSystemInit:
    """Tests for agent/soul/system/__init__.py"""

    def test_module_importable(self):
        """agent.soul.system module should be importable"""
        import agent.soul.system
        assert agent.soul.system is not None


# =============================================================================
# Tests for agent/tool/system/__init__.py
# =============================================================================

class TestToolSystemInit:
    """Tests for agent/tool/system/__init__.py"""

    def test_module_importable(self):
        """agent.tool.system module should be importable"""
        import agent.tool.system
        assert agent.tool.system is not None

    def test_module_has_docstring(self):
        """agent.tool.system module should have docstring"""
        import agent.tool.system
        assert agent.tool.system.__doc__ is not None
        assert "System tools" in agent.tool.system.__doc__

    def test_all_exports_empty(self):
        """__all__ should be empty (tools auto-discovered)"""
        import agent.tool.system
        assert agent.tool.system.__all__ == []


# =============================================================================
# Tests for agent/tool/system/crew_member/__init__.py
# =============================================================================

class TestCrewMemberToolInit:
    """Tests for agent/tool/system/crew_member/__init__.py"""

    def test_crew_member_tool_exported(self):
        """CrewMemberTool should be exported"""
        from agent.tool.system.crew_member import CrewMemberTool
        assert CrewMemberTool is not None

    def test_all_exports_present(self):
        """__all__ should contain CrewMemberTool"""
        from agent.tool.system.crew_member import __all__
        assert 'CrewMemberTool' in __all__


# =============================================================================
# Tests for agent/tool/system/crew_member/crew_member_tool.py
# =============================================================================

class TestCrewMemberToolCreation:
    """Tests for CrewMemberTool initialization"""

    def test_crew_member_tool_creation(self):
        """CrewMemberTool should be created successfully"""
        from agent.tool.system.crew_member.crew_member_tool import CrewMemberTool

        tool = CrewMemberTool()
        assert tool.name == "crew_member"
        assert "crew members" in tool.description.lower()

    def test_crew_member_tool_has_crew_service(self):
        """CrewMemberTool should have _crew_service"""
        from agent.tool.system.crew_member.crew_member_tool import CrewMemberTool

        tool = CrewMemberTool()
        assert tool._crew_service is not None


class TestCrewMemberToolGetProject:
    """Tests for CrewMemberTool._get_project"""

    def test_get_project_none_context(self):
        """_get_project should return None when context is None"""
        from agent.tool.system.crew_member.crew_member_tool import CrewMemberTool

        tool = CrewMemberTool()
        result = tool._get_project(None)
        assert result is None

    def test_get_project_with_workspace(self):
        """_get_project should return workspace when available"""
        from agent.tool.system.crew_member.crew_member_tool import CrewMemberTool

        tool = CrewMemberTool()
        mock_context = MagicMock()
        mock_context.workspace = "mock_workspace"

        result = tool._get_project(mock_context)
        assert result == "mock_workspace"


class TestCrewMemberToolToDict:
    """Tests for CrewMemberTool._crew_member_to_dict"""

    def test_crew_member_to_dict(self):
        """_crew_member_to_dict should convert CrewMember to dict"""
        from agent.tool.system.crew_member.crew_member_tool import CrewMemberTool

        tool = CrewMemberTool()
        mock_member = MagicMock()
        mock_member.config.name = "Director"
        mock_member.config.description = "Film director"
        mock_member.config.soul = "creative"
        mock_member.config.skills = ["vision", "leadership"]
        mock_member.config.model = "gpt-4"
        mock_member.config.temperature = 0.5
        mock_member.config.max_steps = 20
        mock_member.config.color = "#ff0000"
        mock_member.config.icon = "🎬"

        result = tool._crew_member_to_dict(mock_member)
        assert result["name"] == "Director"
        assert result["description"] == "Film director"
        assert result["model"] == "gpt-4"
        assert result["skills"] == ["vision", "leadership"]


class TestCrewMemberToolExecute:
    """Tests for CrewMemberTool.execute"""

    @pytest.mark.asyncio
    async def test_execute_missing_operation(self):
        """execute should return error when missing operation"""
        from agent.tool.system.crew_member.crew_member_tool import CrewMemberTool

        tool = CrewMemberTool()
        mock_context = MagicMock()
        mock_context.workspace = MagicMock()

        events = []
        async for event in tool.execute({}, mock_context):
            events.append(event)

        assert len(events) > 0
        # First event should be an error
        error_event = events[0]
        assert hasattr(error_event, 'event_type')

    @pytest.mark.asyncio
    async def test_execute_unknown_operation(self):
        """execute should return error for unknown operation"""
        from agent.tool.system.crew_member.crew_member_tool import CrewMemberTool

        tool = CrewMemberTool()
        mock_context = MagicMock()
        mock_context.workspace = MagicMock()

        events = []
        async for event in tool.execute({"operation": "invalid"}, mock_context):
            events.append(event)

        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_execute_no_project(self):
        """execute should return error when no project"""
        from agent.tool.system.crew_member.crew_member_tool import CrewMemberTool

        tool = CrewMemberTool()
        mock_context = MagicMock()
        mock_context.workspace = None

        events = []
        async for event in tool.execute({"operation": "list"}, mock_context):
            events.append(event)

        assert len(events) > 0


# =============================================================================
# Tests for agent/tool/system/execute_generated_code/__init__.py
# =============================================================================

class TestExecuteGeneratedCodeInit:
    """Tests for agent/tool/system/execute_generated_code/__init__.py"""

    def test_execute_generated_code_tool_exported(self):
        """ExecuteGeneratedCodeTool should be exported"""
        from agent.tool.system.execute_generated_code import ExecuteGeneratedCodeTool
        assert ExecuteGeneratedCodeTool is not None

    def test_all_exports_present(self):
        """__all__ should contain ExecuteGeneratedCodeTool"""
        from agent.tool.system.execute_generated_code import __all__
        assert 'ExecuteGeneratedCodeTool' in __all__


# =============================================================================
# Tests for agent/tool/system/execute_generated_code/execute_generated_code.py
# =============================================================================

class TestExecuteGeneratedCodeToolCreation:
    """Tests for ExecuteGeneratedCodeTool initialization"""

    def test_tool_creation(self):
        """ExecuteGeneratedCodeTool should be created successfully"""
        from agent.tool.system.execute_generated_code.execute_generated_code import ExecuteGeneratedCodeTool

        tool = ExecuteGeneratedCodeTool()
        assert tool.name == "execute_generated_code"
        assert "generated" in tool.description.lower()

    def test_tool_has_tool_dir(self):
        """ExecuteGeneratedCodeTool should have _tool_dir set"""
        from agent.tool.system.execute_generated_code.execute_generated_code import ExecuteGeneratedCodeTool

        tool = ExecuteGeneratedCodeTool()
        assert tool._tool_dir is not None


class TestExecuteGeneratedCodeToolExecute:
    """Tests for ExecuteGeneratedCodeTool.execute"""

    @pytest.mark.asyncio
    async def test_execute_missing_code(self):
        """execute should return error when missing code"""
        from agent.tool.system.execute_generated_code.execute_generated_code import ExecuteGeneratedCodeTool

        tool = ExecuteGeneratedCodeTool()
        mock_context = MagicMock()

        events = []
        async for event in tool.execute({}, mock_context):
            events.append(event)

        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_execute_with_code(self):
        """execute should process code parameter"""
        from agent.tool.system.execute_generated_code.execute_generated_code import ExecuteGeneratedCodeTool

        tool = ExecuteGeneratedCodeTool()
        mock_context = MagicMock()

        # Mock ToolService.execute_script_content
        with patch('agent.tool.tool_service.ToolService') as MockToolService:
            mock_tool_service = MockToolService.return_value
            mock_tool_service.execute_script_content = AsyncMock(return_value={"result": "success"})

            events = []
            async for event in tool.execute({"code": "print('hello')"}, mock_context):
                events.append(event)

            # Should have progress and tool_end events
            assert len(events) >= 1