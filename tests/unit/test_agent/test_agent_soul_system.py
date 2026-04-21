"""
Unit tests for agent/soul/ module.

Tests for:
- agent/soul/soul.py - Soul class with lazy loading
- agent/soul/soul_service.py - SoulService singleton behavior
- agent/soul/__init__.py - Module exports
"""
import pytest
from typing import Dict, Any, Optional

from agent.soul.soul import Soul
from agent.soul.soul_service import SoulService


class TestSoul:
    """Tests for Soul class"""

    def test_soul_creation_basic(self):
        """Soul should be created with basic fields"""
        soul = Soul(
            name="Creative Soul",
            skills=["writing", "editing"],
            description_file="/path/to/file.md"
        )
        assert soul.name == "Creative Soul"
        assert soul.skills == ["writing", "editing"]
        assert soul.description_file == "/path/to/file.md"

    def test_soul_metadata_lazy_loading(self):
        """Soul.metadata should be None before lazy loading"""
        soul = Soul(
            name="Test Soul",
            skills=["test"],
            description_file="/nonexistent/path.md"
        )
        # Metadata should be None when file doesn't exist
        assert soul._metadata is None

    def test_soul_knowledge_lazy_loading(self):
        """Soul.knowledge should be None before lazy loading"""
        soul = Soul(
            name="Test Soul",
            skills=["test"],
            description_file="/nonexistent/path.md"
        )
        # Knowledge should be None when file doesn't exist
        assert soul._knowledge is None

    def test_soul_repr(self):
        """Soul.__repr__ should return readable string"""
        soul = Soul(
            name="Test",
            skills=["skill1"],
            description_file="/path.md"
        )
        repr_str = repr(soul)
        assert "Soul" in repr_str
        assert "Test" in repr_str
        assert "skill1" in repr_str

    def test_soul_equality_same(self):
        """Soul.__eq__ should return True for identical souls"""
        soul1 = Soul(name="A", skills=["s1"], description_file="/path.md")
        soul2 = Soul(name="A", skills=["s1"], description_file="/path.md")
        assert soul1 == soul2

    def test_soul_equality_different_name(self):
        """Soul.__eq__ should return False for different names"""
        soul1 = Soul(name="A", skills=["s1"], description_file="/path.md")
        soul2 = Soul(name="B", skills=["s1"], description_file="/path.md")
        assert soul1 != soul2

    def test_soul_equality_different_skills(self):
        """Soul.__eq__ should return False for different skills"""
        soul1 = Soul(name="A", skills=["s1"], description_file="/path.md")
        soul2 = Soul(name="A", skills=["s2"], description_file="/path.md")
        assert soul1 != soul2

    def test_soul_equality_different_type(self):
        """Soul.__eq__ should return False for non-Soul"""
        soul = Soul(name="A", skills=["s1"], description_file="/path.md")
        assert soul != "not a soul"
        assert soul != None
        assert soul != {"name": "A"}


class TestSoulService:
    """Tests for SoulService singleton"""

    def test_soul_service_singleton(self):
        """SoulService should be singleton"""
        s1 = SoulService()
        s2 = SoulService()
        assert s1 is s2

    def test_soul_service_initial_state(self):
        """SoulService should have correct initial state"""
        service = SoulService()
        # Note: _initialized is True after first creation, workspace can be None
        assert service.workspace is None

    def test_soul_service_get_project_language_default(self):
        """get_project_language should return 'en_US' when no workspace"""
        service = SoulService()
        language = service.get_project_language("test_project")
        assert language == "en_US"

    def test_soul_service_get_all_souls_returns_list(self):
        """get_all_souls should return a list"""
        service = SoulService()
        souls = service.get_all_souls("test_project")
        assert isinstance(souls, list)
        # Returns copy so modifications don't affect original
        souls.append("test")
        assert "test" not in service.project_souls.get("test_project", [])

    def test_soul_service_get_soul_by_name_not_found(self):
        """get_soul_by_name should return None for unknown soul"""
        service = SoulService()
        soul = service.get_soul_by_name("test_project", "nonexistent_soul_name_xyz")
        assert soul is None

    def test_soul_service_search_souls_by_skill_returns_list(self):
        """search_souls_by_skill should return a list"""
        service = SoulService()
        souls = service.search_souls_by_skill("test_project", "writing_xyz_nonexistent")
        assert isinstance(souls, list)

    def test_soul_service_add_soul_to_new_project(self):
        """add_soul should add soul to a new project key"""
        service = SoulService()
        # Use a unique project name to avoid conflicts
        unique_project = f"unique_test_project_add_{id(service)}"
        service.project_souls[unique_project] = []
        soul = Soul(name="Test Soul", skills=["test"], description_file="/path.md")
        result = service.add_soul(unique_project, soul)
        assert result is True
        assert len(service.project_souls[unique_project]) == 1

    def test_soul_service_add_soul_duplicate(self):
        """add_soul should return False for duplicate soul"""
        service = SoulService()
        unique_project = f"unique_test_project_dup_{id(service)}"
        service.project_souls[unique_project] = []
        soul = Soul(name="Test", skills=["s1"], description_file="/path.md")
        service.add_soul(unique_project, soul)
        # Try to add same soul again
        soul2 = Soul(name="Test", skills=["s2"], description_file="/path2.md")
        result = service.add_soul(unique_project, soul2)
        assert result is False

    def test_soul_service_update_soul(self):
        """update_soul should update existing soul"""
        service = SoulService()
        unique_project = f"unique_test_project_upd_{id(service)}"
        service.project_souls[unique_project] = []
        soul = Soul(name="Test", skills=["s1"], description_file="/path.md")
        service.add_soul(unique_project, soul)
        # Update the soul
        updated = Soul(name="Test", skills=["s1", "s2"], description_file="/path2.md")
        result = service.update_soul(unique_project, "Test", updated)
        assert result is True
        assert service.project_souls[unique_project][0].skills == ["s1", "s2"]

    def test_soul_service_update_soul_not_found(self):
        """update_soul should return False for unknown soul"""
        service = SoulService()
        unique_project = f"unique_test_project_upd_nf_{id(service)}"
        service.project_souls[unique_project] = []
        updated = Soul(name="New", skills=["s1"], description_file="/path.md")
        result = service.update_soul(unique_project, "Nonexistent", updated)
        assert result is False

    def test_soul_service_delete_soul(self):
        """delete_soul should remove soul"""
        service = SoulService()
        unique_project = f"unique_test_project_del_{id(service)}"
        service.project_souls[unique_project] = []
        soul = Soul(name="Test", skills=["s1"], description_file="/path.md")
        service.add_soul(unique_project, soul)
        result = service.delete_soul(unique_project, "Test")
        assert result is True
        assert len(service.project_souls[unique_project]) == 0

    def test_soul_service_delete_soul_not_found(self):
        """delete_soul should return False for unknown soul"""
        service = SoulService()
        unique_project = f"unique_test_project_del_nf_{id(service)}"
        service.project_souls[unique_project] = []
        result = service.delete_soul(unique_project, "Nonexistent")
        assert result is False

    def test_soul_service_refresh_souls_for_project(self):
        """refresh_souls_for_project should return True"""
        service = SoulService()
        result = service.refresh_souls_for_project("test_project")
        # Returns True even when no souls loaded (empty project)
        assert result is True

    def test_soul_service_get_available_languages(self):
        """get_available_languages should return list"""
        service = SoulService()
        languages = service.get_available_languages()
        assert isinstance(languages, list)


class TestSoulInitExports:
    """Tests for agent/soul/__init__.py exports"""

    def test_soul_exported(self):
        """Soul should be exported from soul package"""
        from agent.soul import Soul
        assert Soul is not None

    def test_soul_service_exported(self):
        """SoulService should be exported from soul package"""
        from agent.soul import SoulService
        assert SoulService is not None

    def test_soul_service_instance_exported(self):
        """soul_service instance should be exported"""
        from agent.soul import soul_service
        assert soul_service is not None