"""
Unit tests for chat service in server/service/chat_service.py
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import time

from server.service.chat_service import (
    ChatService,
    _is_chat_capable,
    _advertised_chat_model_ids,
    CHAT_SERVER_TYPES,
)
from server.api.types import Ability, SelectionMode
from server.api.chat_types import (
    ChatCompletionRequest,
    ChatMessage,
    ModelInfo,
)


class TestChatServerTypes:
    """Tests for CHAT_SERVER_TYPES constant"""

    def test_chat_server_types_contains_expected_types(self):
        """Verify expected server types are included"""
        expected = {"chat", "openai", "llm", "bailian"}
        assert expected.issubset(CHAT_SERVER_TYPES)


class TestIsChatCapable:
    """Tests for _is_chat_capable helper function"""

    def test_returns_true_for_chat_server_types(self):
        """Verify chat server types are recognized"""
        mock_config = Mock()
        for server_type in CHAT_SERVER_TYPES:
            mock_config.server_type = server_type
            mock_config.parameters = {}
            assert _is_chat_capable(mock_config) == True

    def test_returns_true_for_dashscope_provider(self):
        """Verify dashscope provider is recognized"""
        mock_config = Mock()
        mock_config.server_type = "other"
        mock_config.parameters = {"provider": "dashscope"}
        assert _is_chat_capable(mock_config) == True

    def test_returns_true_when_chat_enabled(self):
        """Verify chat_enabled parameter is recognized"""
        mock_config = Mock()
        mock_config.server_type = "other"
        mock_config.parameters = {"chat_enabled": True}
        assert _is_chat_capable(mock_config) == True

    def test_returns_false_for_non_chat_servers(self):
        """Verify non-chat servers return False"""
        mock_config = Mock()
        mock_config.server_type = "image-server"
        mock_config.parameters = {}
        assert _is_chat_capable(mock_config) == False


class TestAdvertisedChatModelIds:
    """Tests for _advertised_chat_model_ids helper function"""

    def test_returns_models_from_parameters(self):
        """Verify models from parameters are returned"""
        mock_config = Mock()
        mock_config.parameters = {
            "models": ["gpt-4", "gpt-3.5-turbo"]
        }

        with patch(
            "server.service.chat_service.is_model_enabled_for_ability",
            return_value=True,
        ):
            result = _advertised_chat_model_ids(mock_config)
            assert "gpt-4" in result
            assert "gpt-3.5-turbo" in result

    def test_includes_default_model(self):
        """Verify default_model is included"""
        mock_config = Mock()
        mock_config.parameters = {
            "models": ["gpt-4"],
            "default_model": "gpt-3.5-turbo"
        }

        with patch(
            "server.service.chat_service.is_model_enabled_for_ability",
            return_value=True,
        ):
            result = _advertised_chat_model_ids(mock_config)
            assert "gpt-3.5-turbo" in result

    def test_filters_by_enabled_ability(self):
        """Verify models are filtered by is_model_enabled_for_ability"""
        mock_config = Mock()
        mock_config.parameters = {
            "models": ["enabled-model", "disabled-model"]
        }

        def mock_enabled_check(params, ability, model):
            return model == "enabled-model"

        with patch(
            "server.service.chat_service.is_model_enabled_for_ability",
            side_effect=mock_enabled_check,
        ):
            result = _advertised_chat_model_ids(mock_config)
            assert result == ["enabled-model"]


class TestChatServiceInit:
    """Tests for ChatService initialization"""

    def test_init_with_server_manager(self):
        """Verify initialization with ServerManager"""
        mock_manager = Mock()
        service = ChatService(mock_manager)
        assert service._server_manager == mock_manager
        assert service._selection_service is None

    def test_selection_service_lazy_initialization(self):
        """Verify selection service is lazily initialized"""
        mock_manager = Mock()
        service = ChatService(mock_manager)

        # First access should initialize
        from server.service.ability_selection_service import AbilitySelectionService
        with patch.object(
            AbilitySelectionService, "__init__", return_value=None
        ) as mock_init:
            mock_init.side_effect = lambda mgr: None
            ss = service.selection_service
            # Service should be initialized (object exists)
            assert service._selection_service is not None


class TestChatServiceListModels:
    """Tests for list_models method"""

    def test_list_models_returns_empty_for_no_servers(self):
        """Verify empty list when no servers"""
        mock_manager = Mock()
        mock_manager.list_servers.return_value = []
        service = ChatService(mock_manager)

        result = service.list_models()
        assert result == []

    def test_list_models_skips_disabled_servers(self):
        """Verify disabled servers are skipped"""
        mock_manager = Mock()

        disabled_server = Mock()
        disabled_server.config = Mock()
        disabled_server.config.enabled = False

        mock_manager.list_servers.return_value = [disabled_server]
        service = ChatService(mock_manager)

        result = service.list_models()
        assert result == []

    def test_list_models_skips_non_chat_servers(self):
        """Verify non-chat servers are skipped"""
        mock_manager = Mock()

        non_chat_server = Mock()
        non_chat_server.config = Mock()
        non_chat_server.config.enabled = True
        non_chat_server.config.server_type = "image-server"
        non_chat_server.config.name = "image-server"
        non_chat_server.config.parameters = {}

        mock_manager.list_servers.return_value = [non_chat_server]
        service = ChatService(mock_manager)

        result = service.list_models()
        assert result == []

    def test_list_models_aggregates_from_chat_servers(self):
        """Verify models are aggregated from chat servers"""
        mock_manager = Mock()

        chat_server1 = Mock()
        chat_server1.config = Mock()
        chat_server1.config.enabled = True
        chat_server1.config.server_type = "openai"
        chat_server1.config.name = "openai-server"
        chat_server1.config.parameters = {"models": ["gpt-4"]}

        chat_server2 = Mock()
        chat_server2.config = Mock()
        chat_server2.config.enabled = True
        chat_server2.config.server_type = "chat"
        chat_server2.config.name = "chat-server"
        chat_server2.config.parameters = {"models": ["claude"]}

        mock_manager.list_servers.return_value = [chat_server1, chat_server2]
        service = ChatService(mock_manager)

        with patch(
            "server.service.chat_service.is_model_enabled_for_ability",
            return_value=True,
        ):
            result = service.list_models()

        # Should have both models
        assert len(result) == 2
        model_ids = [m.id for m in result]
        assert "gpt-4" in model_ids
        assert "claude" in model_ids

    def test_list_models_deduplicates(self):
        """Verify duplicate models are deduplicated"""
        mock_manager = Mock()

        server1 = Mock()
        server1.config = Mock()
        server1.config.enabled = True
        server1.config.server_type = "openai"
        server1.config.name = "server1"
        server1.config.parameters = {"models": ["gpt-4"]}

        server2 = Mock()
        server2.config = Mock()
        server2.config.enabled = True
        server2.config.server_type = "openai"
        server2.config.name = "server2"
        server2.config.parameters = {"models": ["gpt-4"]}

        mock_manager.list_servers.return_value = [server1, server2]
        service = ChatService(mock_manager)

        with patch(
            "server.service.chat_service.is_model_enabled_for_ability",
            return_value=True,
        ):
            result = service.list_models()

        # Should deduplicate
        assert len(result) == 1
        assert result[0].id == "gpt-4"


class TestChatServiceResolveServerAndModel:
    """Tests for _resolve_server_and_model method"""

    def test_resolve_uses_selection_service(self):
        """Verify selection service is used for resolution"""
        mock_manager = Mock()

        # Mock server
        mock_server = Mock()
        mock_server.is_enabled = True
        mock_server.config = Mock()
        mock_server.config.name = "test-server"
        mock_manager.get_server.return_value = mock_server

        service = ChatService(mock_manager)

        # Mock selection service
        mock_selection_result = Mock()
        mock_selection_result.server_name = "test-server"
        mock_selection_result.model_name = "test-model"
        mock_selection_result.mode_used = SelectionMode.AUTO
        mock_selection_result.selection_reason = "auto selection"

        mock_ss = Mock()
        mock_ss.select.return_value = mock_selection_result
        service._selection_service = mock_ss

        request = ChatCompletionRequest(
            model="test-model",
            messages=[ChatMessage(role="user", content="test")],
        )

        server_cfg, model_name = service._resolve_server_and_model(request)

        mock_ss.select.assert_called_once()
        assert model_name == "test-model"

    def test_resolve_raises_for_disabled_server(self):
        """Verify error raised when selected server is disabled"""
        mock_manager = Mock()

        # Mock disabled server
        mock_server = Mock()
        mock_server.is_enabled = False
        mock_manager.get_server.return_value = mock_server

        service = ChatService(mock_manager)

        mock_selection_result = Mock()
        mock_selection_result.server_name = "disabled-server"
        mock_selection_result.model_name = "model"

        mock_ss = Mock()
        mock_ss.select.return_value = mock_selection_result
        service._selection_service = mock_ss

        request = ChatCompletionRequest(
            model="model",
            messages=[ChatMessage(role="user", content="test")],
        )

        with pytest.raises(ValueError, match="not found or disabled"):
            service._resolve_server_and_model(request)


class TestChatServiceConvertToResponse:
    """Tests for _convert_to_response method"""

    def test_convert_creates_response_from_result(self):
        """Verify TaskResult is converted to ChatCompletionResponse"""
        mock_manager = Mock()
        service = ChatService(mock_manager)

        # Mock TaskResult
        result = Mock()
        result.task_id = "task-123"
        result.status = "success"
        result.metadata = {
            "text": "Hello, world!",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
            "filmeto_server": "test-server",
            "filmeto_model": "test-model",
        }

        response = service._convert_to_response(result, "test-model")

        assert response.id == "task-123"
        assert response.model == "test-model"
        assert response.choices[0].message.content == "Hello, world!"
        assert response.usage.prompt_tokens == 10
        assert response.filmeto_server == "test-server"

    def test_convert_handles_missing_metadata(self):
        """Verify conversion handles missing metadata gracefully"""
        mock_manager = Mock()
        service = ChatService(mock_manager)

        result = Mock()
        result.task_id = "task-123"
        result.status = "success"
        result.metadata = None

        response = service._convert_to_response(result, "model")

        assert response.choices[0].message.content == ""
        assert response.usage.prompt_tokens == 0


class TestChatServiceAnnotateMetadata:
    """Tests for _annotate_chat_task_metadata method"""

    def test_annotate_adds_server_and_model_info(self):
        """Verify metadata is annotated with server info"""
        mock_manager = Mock()
        service = ChatService(mock_manager)

        result = Mock()
        result.metadata = {}

        server_cfg = Mock()
        server_cfg.name = "test-server"

        service._annotate_chat_task_metadata(result, server_cfg, "requested-model")

        assert result.metadata["filmeto_server"] == "test-server"
        assert "filmeto_model" in result.metadata

    def test_annotate_preserves_actual_model(self):
        """Verify actual_model from metadata is preserved"""
        mock_manager = Mock()
        service = ChatService(mock_manager)

        result = Mock()
        result.metadata = {"actual_model": "actual-model"}

        server_cfg = Mock()
        server_cfg.name = "test-server"

        service._annotate_chat_task_metadata(result, server_cfg, "requested-model")

        # Should use actual_model from metadata
        assert result.metadata["filmeto_model"] == "actual-model"