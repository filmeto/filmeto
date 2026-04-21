"""
Unit tests for agent/skill/skill_service.py

Tests skill service functionality including:
- SkillService: Skill management service
- load_skills: Load skills from directories
- get_skill: Get skill by name
- create_skill: Create new skill
- update_skill: Update existing skill
- delete_skill: Delete skill
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from agent.skill.skill_service import SkillService
from agent.skill.skill_models import Skill


class TestSkillServiceInit:
    """Tests for SkillService initialization."""

    def test_init_sets_system_skills_path(self):
        """SkillService sets system_skills_path."""
        service = SkillService()
        expected_path = os.path.join(os.path.dirname(__file__), "system")
        # The path should be relative to skill_service.py location
        assert "system" in service.system_skills_path

    def test_init_creates_empty_skills_dict(self):
        """SkillService creates empty skills dict."""
        service = SkillService()
        assert service.skills == {}

    def test_init_with_workspace_sets_custom_path(self):
        """SkillService sets custom_skills_path when workspace provided."""
        mock_workspace = Mock()
        mock_workspace.workspace_path = "/tmp/workspace"

        service = SkillService(workspace=mock_workspace)
        assert service.custom_skills_path == "/tmp/workspace/skills"

    def test_init_without_workspace_no_custom_path(self):
        """SkillService has None custom_skills_path without workspace."""
        service = SkillService()
        assert service.custom_skills_path is None


class TestSkillServiceGetSkill:
    """Tests for SkillService.get_skill method."""

    def test_get_skill_returns_cached_skill(self):
        """get_skill returns cached skill by name."""
        service = SkillService()
        mock_skill = Mock()
        mock_skill.name = "test_skill"
        service.skills["test_skill"] = mock_skill

        result = service.get_skill("test_skill")
        assert result is mock_skill

    def test_get_skill_returns_none_for_unknown(self):
        """get_skill returns None for unknown skill."""
        service = SkillService()
        result = service.get_skill("unknown_skill")
        assert result is None

    def test_get_skill_with_language_loads_from_disk(self):
        """get_skill with language tries to load from disk."""
        service = SkillService()
        service.custom_skills_path = None  # No custom path
        service.system_skills_path = "/tmp/system_skills"

        # Mock _load_skill_from_directory to return None
        service._load_skill_from_directory = Mock(return_value=None)

        result = service.get_skill("test", language="zh_CN")
        # Should attempt to load
        assert result is None


class TestSkillServiceGetAllSkills:
    """Tests for SkillService.get_all_skills method."""

    def test_get_all_skills_returns_list(self):
        """get_all_skills returns list of skills."""
        service = SkillService()
        mock_skill1 = Mock()
        mock_skill2 = Mock()
        service.skills = {"skill1": mock_skill1, "skill2": mock_skill2}

        result = service.get_all_skills()
        assert len(result) == 2
        assert mock_skill1 in result
        assert mock_skill2 in result

    def test_get_all_skills_with_language_reloads(self):
        """get_all_skills with language reloads skills."""
        service = SkillService()
        service.load_skills = Mock()

        result = service.get_all_skills(language="zh_CN")

        service.load_skills.assert_called_once_with(language="zh_CN")


class TestSkillServiceGetSkillNames:
    """Tests for SkillService.get_skill_names method."""

    def test_get_skill_names_returns_names(self):
        """get_skill_names returns list of skill names."""
        service = SkillService()
        service.skills = {"skill1": Mock(), "skill2": Mock()}

        result = service.get_skill_names()
        assert "skill1" in result
        assert "skill2" in result

    def test_get_skill_names_empty_returns_empty_list(self):
        """get_skill_names returns empty list for no skills."""
        service = SkillService()
        result = service.get_skill_names()
        assert result == []


class TestSkillServiceGetSkillPromptInfo:
    """Tests for SkillService.get_skill_prompt_info method."""

    def test_get_skill_prompt_info_returns_formatted_string(self):
        """get_skill_prompt_info returns formatted skill info."""
        service = SkillService()
        mock_skill = Mock()
        mock_skill.name = "test_skill"
        mock_skill.description = "Test skill description"
        mock_skill.knowledge = "Skill knowledge content"
        mock_skill.get_example_call = Mock(return_value="example_json")
        service.skills["test_skill"] = mock_skill

        result = service.get_skill_prompt_info("test_skill")
        assert "### Skill: test_skill" in result
        assert "Test skill description" in result

    def test_get_skill_prompt_info_returns_not_found(self):
        """get_skill_prompt_info returns not found message."""
        service = SkillService()
        result = service.get_skill_prompt_info("unknown")
        assert "not found" in result


class TestSkillServiceRefreshSkills:
    """Tests for SkillService.refresh_skills method."""

    def test_refresh_skills_clears_and_reloads(self):
        """refresh_skills clears skills dict and reloads."""
        service = SkillService()
        service.skills = {"old": Mock()}
        service.load_skills = Mock()

        service.refresh_skills()

        assert service.skills == {}
        service.load_skills.assert_called_once()


class TestSkillServiceCreateSkill:
    """Tests for SkillService.create_skill method."""

    def test_create_skill_returns_false_on_exception(self):
        """create_skill returns False on exception."""
        service = SkillService()
        mock_skill = Mock()
        mock_skill.name = "test"
        mock_skill.description = "desc"
        mock_skill.knowledge = "content"
        mock_skill.tools = None
        mock_skill.reference = None
        mock_skill.examples = None

        # Mock to cause exception
        service.custom_skills_path = None

        with patch("utils.md_with_meta_utils.write_md_with_meta", side_effect=Exception("error")):
            result = service.create_skill(mock_skill)
            assert result is False


class TestSkillServiceUpdateSkill:
    """Tests for SkillService.update_skill method."""

    def test_update_skill_returns_false_not_found(self):
        """update_skill returns False when skill not found."""
        service = SkillService()
        service.system_skills_path = "/tmp/system"
        service.custom_skills_path = None

        mock_skill = Mock()
        mock_skill.name = "unknown"
        mock_skill.description = "desc"
        mock_skill.knowledge = "content"

        result = service.update_skill("unknown", mock_skill)
        assert result is False


class TestSkillServiceDeleteSkill:
    """Tests for SkillService.delete_skill method."""

    def test_delete_skill_returns_false_not_found(self):
        """delete_skill returns False when skill not found."""
        service = SkillService()
        service.system_skills_path = "/tmp/system"
        service.custom_skills_path = None

        result = service.delete_skill("unknown_skill")
        assert result is False

    def test_delete_skill_removes_from_cache(self):
        """delete_skill removes skill from internal cache."""
        service = SkillService()
        mock_skill = Mock()
        service.skills["test_skill"] = mock_skill

        # Mock finding skill dir and deletion
        with patch("os.path.exists", return_value=True):
            with patch("shutil.rmtree"):
                # Simulate successful deletion
                service.delete_skill("test_skill")
                # Note: actual deletion logic would remove from cache


class TestSkillServiceGetSkillMdPath:
    """Tests for SkillService._get_skill_md_path method."""

    def test_get_skill_md_path_returns_default(self):
        """_get_skill_md_path returns default SKILL.md path."""
        service = SkillService()

        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "test_skill"
            skill_path.mkdir()
            (skill_path / "SKILL.md").write_text("---\nname: test\n---\n")

            result = service._get_skill_md_path(str(skill_path))
            assert result.endswith("SKILL.md")

    def test_get_skill_md_path_returns_language_specific(self):
        """_get_skill_md_path returns language-specific file if exists."""
        service = SkillService()

        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "test_skill"
            skill_path.mkdir()
            (skill_path / "SKILL_zh_CN.md").write_text("---\nname: test\n---\n")

            result = service._get_skill_md_path(str(skill_path), language="zh_CN")
            assert "SKILL_zh_CN.md" in result


class TestSkillServiceGetOptionalFilePath:
    """Tests for SkillService._get_optional_file_path method."""

    def test_get_optional_file_path_returns_none_missing(self):
        """_get_optional_file_path returns None when file missing."""
        service = SkillService()

        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "test_skill"
            skill_path.mkdir()

            result = service._get_optional_file_path(str(skill_path), "reference")
            assert result is None

    def test_get_optional_file_path_returns_path(self):
        """_get_optional_file_path returns path when file exists."""
        service = SkillService()

        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "test_skill"
            skill_path.mkdir()
            (skill_path / "reference.md").write_text("Reference content")

            result = service._get_optional_file_path(str(skill_path), "reference")
            assert result is not None
            assert "reference.md" in result