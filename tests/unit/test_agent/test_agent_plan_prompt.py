"""
Unit tests for agent/plan/plan_signals.py and agent/prompt/prompt_service.py.

Tests for:
- PlanSignalManager singleton and signals
- PromptService template loading and caching
- Module exports
"""
import pytest
from typing import Dict, Any, Optional


class TestPlanSignalManager:
    """Tests for PlanSignalManager singleton"""

    def test_plan_signal_manager_singleton(self):
        """PlanSignalManager should be singleton"""
        from agent.plan.plan_signals import PlanSignalManager
        s1 = PlanSignalManager.get_instance()
        s2 = PlanSignalManager.get_instance()
        assert s1 is s2

    def test_plan_signal_manager_has_signals(self):
        """PlanSignalManager should have signal attributes"""
        from agent.plan.plan_signals import PlanSignalManager
        manager = PlanSignalManager.get_instance()
        assert hasattr(manager, 'plan_created')
        assert hasattr(manager, 'plan_updated')
        assert hasattr(manager, 'plan_deleted')
        assert hasattr(manager, 'plan_instance_created')
        assert hasattr(manager, 'plan_instance_status_updated')
        assert hasattr(manager, 'plan_task_updated')

    def test_plan_signal_manager_global_instance(self):
        """plan_signal_manager global instance should exist"""
        from agent.plan.plan_signals import plan_signal_manager
        assert plan_signal_manager is not None


class TestPromptService:
    """Tests for PromptService"""

    def test_prompt_service_instance(self):
        """PromptService should be instantiable"""
        from agent.prompt.prompt_service import PromptService
        service = PromptService()
        assert service is not None

    def test_prompt_service_template_cache(self):
        """PromptService should have template cache"""
        from agent.prompt.prompt_service import PromptService
        service = PromptService()
        assert hasattr(service, '_template_cache')
        assert isinstance(service._template_cache, dict)

    def test_prompt_service_clear_cache(self):
        """PromptService.clear_cache should work"""
        from agent.prompt.prompt_service import PromptService
        service = PromptService()
        # Add something to cache
        service._template_cache["test_key"] = "test_value"
        assert len(service._template_cache) > 0
        service.clear_cache()
        assert len(service._template_cache) == 0

    def test_prompt_service_list_available_prompts_returns_list(self):
        """PromptService.list_available_prompts should return list"""
        from agent.prompt.prompt_service import PromptService
        service = PromptService()
        prompts = service.list_available_prompts()
        assert isinstance(prompts, list)

    def test_prompt_service_get_prompt_template_not_found(self):
        """PromptService.get_prompt_template should return None for nonexistent"""
        from agent.prompt.prompt_service import PromptService
        service = PromptService()
        template = service.get_prompt_template("nonexistent_template_xyz")
        assert template is None

    def test_prompt_service_get_prompt_metadata_not_found(self):
        """PromptService.get_prompt_metadata should return None for nonexistent"""
        from agent.prompt.prompt_service import PromptService
        service = PromptService()
        metadata = service.get_prompt_metadata("nonexistent_template_xyz")
        assert metadata is None

    def test_prompt_service_render_prompt_not_found(self):
        """PromptService.render_prompt should return None for nonexistent"""
        from agent.prompt.prompt_service import PromptService
        service = PromptService()
        result = service.render_prompt("nonexistent_template_xyz")
        assert result is None

    def test_prompt_service_global_instance(self):
        """prompt_service global instance should exist"""
        from agent.prompt.prompt_service import prompt_service
        assert prompt_service is not None


class TestPlanInitExports:
    """Tests for agent/plan/__init__.py exports"""

    def test_plan_service_exported(self):
        """PlanService should be exported from plan package"""
        from agent.plan import PlanService
        assert PlanService is not None

    def test_plan_models_exported(self):
        """Plan models should be exported"""
        from agent.plan import Plan, PlanTask, PlanInstance, PlanStatus, TaskStatus
        assert Plan is not None
        assert PlanTask is not None
        assert PlanInstance is not None
        assert PlanStatus is not None
        assert TaskStatus is not None


class TestPromptInitExports:
    """Tests for agent/prompt/__init__.py exports"""

    def test_prompt_service_importable(self):
        """PromptService should be importable from prompt package"""
        from agent.prompt.prompt_service import PromptService
        assert PromptService is not None

    def test_prompt_service_instance_importable(self):
        """prompt_service instance should be importable"""
        from agent.prompt.prompt_service import prompt_service
        assert prompt_service is not None