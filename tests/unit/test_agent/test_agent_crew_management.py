"""
Unit tests for agent/crew/ module.

Tests for:
- agent/crew/crew_member.py - CrewMember and CrewMemberConfig
- agent/crew/crew_service.py - CrewService singleton and CRUD
- agent/crew/crew_title.py - CrewTitle class and sorting
- agent/crew/__init__.py - Module exports
"""
import pytest
from pathlib import Path
from typing import Dict, Any

# Import crew module components
from agent.crew.crew_title import CrewTitle, sort_crew_members_by_title_importance


class TestCrewTitle:
    """Tests for CrewTitle class"""

    def test_crew_title_creation_basic(self):
        """CrewTitle should be created with title"""
        title = CrewTitle(title="director")
        assert title.title == "director"

    def test_crew_title_creation_with_metadata(self):
        """CrewTitle should accept metadata"""
        metadata = {
            "name": "Director",
            "description": "Film director",
            "skills": ["vision", "leadership"],
            "model": "gpt-4",
            "temperature": 0.4
        }
        title = CrewTitle(title="director", metadata=metadata)
        assert title.name == "Director"
        assert title.description == "Film director"
        assert title.skills == ["vision", "leadership"]
        assert title.model == "gpt-4"

    def test_crew_title_defaults_from_metadata(self):
        """CrewTitle should use defaults when metadata missing"""
        title = CrewTitle(title="unknown")
        assert title.model == "gpt-4o-mini"
        assert title.temperature == 0.4
        assert title.color == "#4a90e2"
        assert title.icon == "🤖"

    def test_crew_title_get_title_display_fallback(self):
        """CrewTitle.get_title_display should fallback to hardcoded mappings"""
        title = CrewTitle(title="director")
        # Test with English
        display = title.get_title_display(lang_code="en")
        assert display == "Director"

    def test_crew_title_get_title_display_chinese(self):
        """CrewTitle.get_title_display should return Chinese"""
        title = CrewTitle(title="director")
        display = title.get_title_display(lang_code="zh")
        assert display == "导演"

    def test_crew_title_get_importance_order_static(self):
        """CrewTitle.get_importance_order should return static order"""
        order = CrewTitle.get_importance_order(use_dynamic=False)
        assert "producer" in order
        assert "director" in order
        assert order.index("producer") < order.index("director")

    def test_crew_title_get_importance_order_length(self):
        """CrewTitle.get_importance_order should have 9 static titles"""
        order = CrewTitle.get_importance_order(use_dynamic=False)
        assert len(order) == 9

    def test_crew_title_get_title_importance_rank_known(self):
        """CrewTitle.get_title_importance_rank should return index for known titles"""
        rank = CrewTitle.get_title_importance_rank("director", use_dynamic=False)
        assert rank == 1  # director is second most important

    def test_crew_title_get_title_importance_rank_unknown(self):
        """CrewTitle.get_title_importance_rank should return len(order) for unknown"""
        rank = CrewTitle.get_title_importance_rank("unknown_title", use_dynamic=False)
        assert rank == len(CrewTitle.get_importance_order(use_dynamic=False))


class TestSortCrewMembersByTitleImportance:
    """Tests for sort_crew_members_by_title_importance function"""

    def test_sort_crew_members_dict(self):
        """sort_crew_members_by_title_importance should sort dict values"""
        class MockCrewMember:
            def __init__(self, name, crew_title):
                self.config = type('obj', (object,), {
                    'metadata': {'crew_title': crew_title}
                })()
                self.name = name

        members = {
            "a": MockCrewMember("a", "editor"),
            "b": MockCrewMember("b", "director"),
            "c": MockCrewMember("c", "producer")
        }
        sorted_list = sort_crew_members_by_title_importance(members, use_dynamic=False)
        assert sorted_list[0].config.metadata['crew_title'] == "producer"
        assert sorted_list[1].config.metadata['crew_title'] == "director"
        assert sorted_list[2].config.metadata['crew_title'] == "editor"

    def test_sort_crew_members_list(self):
        """sort_crew_members_by_title_importance should sort list"""
        class MockCrewMember:
            def __init__(self, name, crew_title):
                self.config = type('obj', (object,), {
                    'metadata': {'crew_title': crew_title}
                })()
                self.name = name

        members = [
            MockCrewMember("a", "editor"),
            MockCrewMember("b", "director"),
            MockCrewMember("c", "producer")
        ]
        sorted_list = sort_crew_members_by_title_importance(members, use_dynamic=False)
        assert sorted_list[0].config.metadata['crew_title'] == "producer"


class TestCrewService:
    """Tests for CrewService singleton"""

    def test_crew_service_singleton(self):
        """CrewService should be singleton"""
        from agent.crew.crew_service import CrewService
        s1 = CrewService()
        s2 = CrewService()
        assert s1 is s2

    def test_crew_service_get_crew_titles_returns_list(self):
        """CrewService.get_crew_titles should return list of CrewTitle objects"""
        from agent.crew.crew_service import CrewService
        service = CrewService()
        titles = service.get_crew_titles()
        assert isinstance(titles, list)
        # Each item should be a CrewTitle
        for title in titles:
            assert isinstance(title, CrewTitle)

    def test_crew_service_resolve_project_path_none(self):
        """CrewService helper _resolve_project_path should handle None"""
        from agent.crew.crew_service import _resolve_project_path
        result = _resolve_project_path(None)
        assert result is None

    def test_crew_service_resolve_project_path_string(self):
        """CrewService helper _resolve_project_path should handle string"""
        from agent.crew.crew_service import _resolve_project_path
        result = _resolve_project_path("/path/to/project")
        assert result == "/path/to/project"

    def test_crew_service_resolve_project_path_object(self):
        """CrewService helper _resolve_project_path should handle object with project_path"""
        from agent.crew.crew_service import _resolve_project_path
        class MockProject:
            project_path = "/mock/project"
        result = _resolve_project_path(MockProject())
        assert result == "/mock/project"

    def test_crew_service_resolve_project_key_none(self):
        """CrewService helper _resolve_project_key should handle None"""
        from agent.crew.crew_service import _resolve_project_key
        result = _resolve_project_key(None)
        assert result is None

    def test_crew_service_resolve_project_key_project_name(self):
        """CrewService helper _resolve_project_key should use project_name"""
        from agent.crew.crew_service import _resolve_project_key
        class MockProject:
            project_name = "test_project"
        result = _resolve_project_key(MockProject())
        assert result == "test_project"


class TestCrewMemberConfig:
    """Tests for CrewMemberConfig dataclass"""

    def test_crew_member_config_basic(self):
        """CrewMemberConfig should be created with defaults"""
        from agent.crew.crew_member import CrewMemberConfig
        config = CrewMemberConfig(name="Test Agent")
        assert config.name == "Test Agent"
        assert config.model == "gpt-4o-mini"
        assert config.temperature == 0.4
        assert config.skills == []

    def test_crew_member_config_with_all_fields(self):
        """CrewMemberConfig should accept all fields"""
        from agent.crew.crew_member import CrewMemberConfig
        config = CrewMemberConfig(
            id="abc123",
            name="Full Agent",
            description="A complete agent",
            soul="creative_soul",
            skills=["skill1", "skill2"],
            prompt="Custom prompt",
            model="gpt-4",
            temperature=0.7,
            max_steps=20,
            color="#ff0000",
            icon="🎬",
            metadata={"custom": "data"}
        )
        assert config.id == "abc123"
        assert config.name == "Full Agent"
        assert config.soul == "creative_soul"
        assert config.skills == ["skill1", "skill2"]
        assert config.color == "#ff0000"
        assert config.icon == "🎬"


class TestCrewInitExports:
    """Tests for agent/crew/__init__.py exports"""

    def test_crew_member_exported(self):
        """CrewMember should be exported from crew package"""
        from agent.crew import CrewMember
        assert CrewMember is not None

    def test_crew_service_exported(self):
        """CrewService should be exported from crew package"""
        from agent.crew import CrewService
        assert CrewService is not None

    def test_crew_title_exported(self):
        """CrewTitle should be exported from crew package"""
        from agent.crew import CrewTitle
        assert CrewTitle is not None

    def test_crew_member_config_exported(self):
        """CrewMemberConfig should be exported from crew package"""
        from agent.crew import CrewMemberConfig
        assert CrewMemberConfig is not None

    def test_crew_member_history_service_exported(self):
        """crew_member_history_service should be exported from crew package"""
        from agent.crew import crew_member_history_service
        assert crew_member_history_service is not None