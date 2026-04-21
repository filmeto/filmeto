"""
Unit tests for ability service in server/service/ability_service.py
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from server.service.ability_service import AbilityService
from server.api.types import Ability, AbilityInstance, ModelInfo, ModelPricing


class TestAbilityServiceInit:
    """Tests for AbilityService initialization"""

    def test_init_with_server_manager(self):
        """Verify initialization with ServerManager"""
        mock_manager = Mock()
        service = AbilityService(mock_manager)
        assert service.server_manager == mock_manager
        assert service._ability_cache == {}
        assert service._abilities_by_type == {}


class TestAbilityServiceConstants:
    """Tests for ability constants and descriptions"""

    def test_ability_names_mapping(self):
        """Verify ABILITY_NAMES contains all expected abilities"""
        expected = [
            Ability.TEXT2IMAGE,
            Ability.IMAGE2IMAGE,
            Ability.IMAGEEDIT,
            Ability.IMAGE2VIDEO,
            Ability.TEXT2VIDEO,
            Ability.SPEAK2VIDEO,
            Ability.TEXT2SPEAK,
            Ability.TEXT2MUSIC,
            Ability.CHAT_COMPLETION,
        ]
        for ability in expected:
            assert ability in AbilityService.ABILITY_NAMES

    def test_ability_descriptions_mapping(self):
        """Verify ABILITY_DESCRIPTIONS contains all expected abilities"""
        for ability in Ability:
            assert ability in AbilityService.ABILITY_DESCRIPTIONS


class TestAbilityServiceDiscovery:
    """Tests for ability discovery logic"""

    def test_refresh_abilities_skips_disabled_servers(self):
        """Verify disabled servers are skipped during refresh"""
        mock_manager = Mock()

        # Create mock server with is_enabled=False
        mock_server = Mock()
        mock_server.is_enabled = False
        mock_server.name = "disabled-server"

        mock_manager.list_servers.return_value = [mock_server]

        service = AbilityService(mock_manager)
        service.refresh_abilities()

        # No abilities should be discovered
        assert len(service._ability_cache) == 0

    def test_refresh_abilities_clears_cache(self):
        """Verify refresh clears existing cache"""
        mock_manager = Mock()
        mock_manager.list_servers.return_value = []

        service = AbilityService(mock_manager)
        # Pre-populate cache
        service._ability_cache["test"] = Mock()

        service.refresh_abilities()

        assert len(service._ability_cache) == 0
        assert len(service._abilities_by_type) == 0

    def test_refresh_abilities_updates_last_refresh(self):
        """Verify refresh updates timestamp"""
        mock_manager = Mock()
        mock_manager.list_servers.return_value = []

        service = AbilityService(mock_manager)
        service.refresh_abilities()

        assert service._last_refresh is not None
        assert isinstance(service._last_refresh, datetime)


class TestAbilityServiceBuildModelInfos:
    """Tests for _build_model_infos method"""

    def test_build_model_infos_with_plugin_models(self):
        """Verify building ModelInfo from plugin models"""
        mock_manager = Mock()
        service = AbilityService(mock_manager)

        # Mock config
        config = Mock()
        config.name = "test-server"
        config.server_type = "test"
        config.parameters = {}

        # Mock ability_config with models
        ability_config = Mock()
        ability_config.description = "Test ability"
        ability_config.models = [
            {"name": "model-1", "display_name": "Model One", "tags": ["fast"]}
        ]

        with patch.object(
            service, "_filter_model_infos_by_ability_models", return_value=[]
        ):
            model_infos = service._build_model_infos(
                config, Ability.TEXT2IMAGE, ability_config
            )

            # Should have created ModelInfo (but filtered returns empty)
            assert isinstance(model_infos, list)

    def test_build_model_infos_without_plugin_models(self):
        """Verify building ModelInfo from config when no plugin models"""
        mock_manager = Mock()
        service = AbilityService(mock_manager)

        # Mock config with models in parameters
        config = Mock()
        config.name = "test-server"
        config.server_type = "test"
        config.parameters = {
            "models": {
                "text2image": {
                    "model-1": {"display_name": "Model One", "is_default": True}
                }
            }
        }

        # Mock ability_config without models
        ability_config = Mock()
        ability_config.description = "Test ability"
        ability_config.models = None

        with patch.object(
            service, "_filter_model_infos_by_ability_models", side_effect=lambda c, a, m: m
        ):
            model_infos = service._build_model_infos(
                config, Ability.TEXT2IMAGE, ability_config
            )

            assert len(model_infos) == 1
            assert model_infos[0].name == "model-1"


class TestAbilityServiceBuildPricing:
    """Tests for _build_pricing method"""

    def test_build_pricing_returns_none_for_none_input(self):
        """Verify None input returns None"""
        mock_manager = Mock()
        service = AbilityService(mock_manager)

        result = service._build_pricing(None)
        assert result is None

    def test_build_pricing_creates_model_pricing(self):
        """Verify pricing dict is converted to ModelPricing"""
        mock_manager = Mock()
        service = AbilityService(mock_manager)

        pricing_data = {
            "per_call": 0.01,
            "per_input_token": 0.001,
            "per_output_token": 0.002,
            "per_image": 0.05,
        }

        result = service._build_pricing(pricing_data)

        assert isinstance(result, ModelPricing)
        assert result.per_call == 0.01
        assert result.per_input_token == 0.001
        assert result.per_output_token == 0.002
        assert result.per_image == 0.05


class TestAbilityServiceExtractModels:
    """Tests for _extract_models_for_ability method"""

    def test_extract_models_from_dict_config(self):
        """Verify extracting models from dict parameters"""
        mock_manager = Mock()
        service = AbilityService(mock_manager)

        config = Mock()
        config.parameters = {
            "models": {
                "text2image": {"model-a": {"description": "Model A"}}
            }
        }

        result = service._extract_models_for_ability(
            config, Ability.TEXT2IMAGE, "Generate images"
        )

        assert "model-a" in result
        assert result["model-a"]["description"] == "Model A"

    def test_extract_models_from_list_config(self):
        """Verify extracting models from list parameters"""
        mock_manager = Mock()
        service = AbilityService(mock_manager)

        config = Mock()
        config.parameters = {
            "models": ["model-a", "model-b"]
        }

        result = service._extract_models_for_ability(
            config, Ability.TEXT2IMAGE, "Generate images"
        )

        assert "model-a" in result
        assert "model-b" in result

    def test_extract_models_uses_default_model_when_empty(self):
        """Verify default_model is used when no models configured"""
        mock_manager = Mock()
        service = AbilityService(mock_manager)

        config = Mock()
        config.parameters = {
            "default_model": "default-model"
        }

        result = service._extract_models_for_ability(
            config, Ability.TEXT2IMAGE, "Generate images"
        )

        assert "default-model" in result
        assert result["default-model"]["is_default"] == True

    def test_extract_models_fallback_to_default_when_no_config(self):
        """Verify fallback when no models or default_model configured"""
        mock_manager = Mock()
        service = AbilityService(mock_manager)

        config = Mock()
        config.parameters = {}

        result = service._extract_models_for_ability(
            config, Ability.TEXT2IMAGE, "Generate images"
        )

        assert "default" in result
        assert result["default"]["is_default"] == True


class TestAbilityServiceQueries:
    """Tests for ability query methods"""

    def test_get_all_ability_instances_refreshes_on_empty_cache(self):
        """Verify refresh is called when cache is empty"""
        mock_manager = Mock()
        mock_manager.list_servers.return_value = []

        service = AbilityService(mock_manager)

        result = service.get_all_ability_instances()

        # Should have called refresh
        assert service._last_refresh is not None
        assert result == []

    def test_get_ability_instances_by_type_returns_matching(self):
        """Verify filtering by ability type"""
        mock_manager = Mock()
        service = AbilityService(mock_manager)

        # Pre-populate cache
        instance1 = Mock(spec=AbilityInstance)
        instance1.key = "server1:model1"
        instance1.ability_type = Ability.TEXT2IMAGE

        instance2 = Mock(spec=AbilityInstance)
        instance2.key = "server2:model2"
        instance2.ability_type = Ability.CHAT_COMPLETION

        service._ability_cache = {
            "server1:model1": instance1,
            "server2:model2": instance2,
        }
        service._abilities_by_type = {
            Ability.TEXT2IMAGE: ["server1:model1"],
            Ability.CHAT_COMPLETION: ["server2:model2"],
        }

        result = service.get_ability_instances_by_type(Ability.TEXT2IMAGE)

        assert len(result) == 1
        assert result[0].key == "server1:model1"

    def test_get_ability_instance_returns_none_for_missing_key(self):
        """Verify missing key returns None"""
        mock_manager = Mock()
        mock_manager.list_servers.return_value = []

        service = AbilityService(mock_manager)

        result = service.get_ability_instance("missing-key")
        assert result is None


class TestAbilityServiceLLMContext:
    """Tests for get_llm_selection_context method"""

    def test_get_llm_selection_context_returns_empty_when_no_instances(self):
        """Verify empty context when no instances available"""
        mock_manager = Mock()
        mock_manager.list_servers.return_value = []

        service = AbilityService(mock_manager)

        result = service.get_llm_selection_context(Ability.TEXT2IMAGE)

        assert result["available"] == False
        assert "No available abilities" in result["message"]

    def test_get_llm_selection_context_returns_options(self):
        """Verify options are returned when instances available"""
        mock_manager = Mock()
        service = AbilityService(mock_manager)

        # Create mock instance
        instance = Mock(spec=AbilityInstance)
        instance.key = "server:model"
        instance.server_name = "server"
        instance.model_name = "model"
        instance.description = "Test model"
        instance.tags = ["fast"]
        instance.specs = {"resolution": "1024x1024"}
        instance.priority = 10
        instance.pricing = None

        service._ability_cache = {"server:model": instance}
        service._abilities_by_type = {Ability.TEXT2IMAGE: ["server:model"]}

        result = service.get_llm_selection_context(
            Ability.TEXT2IMAGE, user_requirement="fast generation"
        )

        assert result["available"] == True
        assert len(result["options"]) == 1
        assert result["options"][0]["key"] == "server:model"
        assert result["user_requirement"] == "fast generation"