"""
Unit tests for utils/llm_utils.py

Tests LLM utility functions including:
- extract_content: Extract content from LLM response objects
- get_chat_service: Get or create ChatService instance
- validate_llm_config: Validate LLM service configuration
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from utils.llm_utils import extract_content, get_chat_service, validate_llm_config


class TestExtractContent:
    """Tests for extract_content function."""

    def test_extract_content_from_response_with_content(self):
        """Extract content from response with choices and message.content."""
        response = Mock()
        choice = Mock()
        message = Mock()
        message.content = "Hello world"
        choice.message = message
        response.choices = [choice]

        result = extract_content(response)
        assert result == "Hello world"

    def test_extract_content_from_none_content_returns_empty(self):
        """Returns empty string when message.content is None."""
        response = Mock()
        choice = Mock()
        message = Mock()
        message.content = None
        message.reasoning_content = None
        choice.message = message
        response.choices = [choice]

        result = extract_content(response)
        assert result == ""

    def test_extract_content_from_reasoning_content(self):
        """Extract reasoning_content when regular content is None."""
        response = Mock()
        choice = Mock()
        message = Mock()
        message.content = None
        message.reasoning_content = "Reasoning process..."
        choice.message = message
        response.choices = [choice]

        result = extract_content(response)
        assert result == "Reasoning process..."

    def test_extract_content_fallback_to_text_attribute(self):
        """Fallback to choice.text attribute when message not available."""
        response = Mock()
        choice = Mock()
        choice.message = None
        choice.text = "Fallback text"
        response.choices = [choice]

        result = extract_content(response)
        assert result == "Fallback text"

    def test_extract_content_empty_choices(self):
        """Returns empty string for empty choices list."""
        response = Mock()
        response.choices = []

        result = extract_content(response)
        assert result == ""

    def test_extract_content_no_choices_attribute(self):
        """Returns str(response) when no choices attribute."""
        response = "plain text response"
        result = extract_content(response)
        assert result == "plain text response"

    def test_extract_content_none_response(self):
        """Returns empty string for None response."""
        result = extract_content(None)
        assert result == ""

    def test_extract_content_converts_to_string(self):
        """Converts non-string content to string."""
        response = Mock()
        choice = Mock()
        message = Mock()
        message.content = 12345
        choice.message = message
        response.choices = [choice]

        result = extract_content(response)
        assert result == "12345"


class TestGetChatService:
    """Tests for get_chat_service function."""

    @patch("utils.llm_utils.ServerManager")
    @patch("utils.llm_utils.ChatService")
    def test_get_chat_service_with_existing_server_manager(self, mock_chat_service, mock_server_manager):
        """Get ChatService using existing ServerManager singleton."""
        mock_instance = Mock()
        mock_instance.servers = {"server1": Mock()}
        mock_server_manager.get_instance.return_value = mock_instance

        result = get_chat_service()

        mock_server_manager.get_instance.assert_called_once()
        mock_chat_service.assert_called_once_with(mock_instance)

    @patch("utils.llm_utils.ServerManager")
    @patch("utils.llm_utils.PluginManager")
    @patch("utils.llm_utils.ChatService")
    def test_get_chat_service_creates_new_manager(self, mock_chat_service, mock_plugin_manager, mock_server_manager):
        """Create new ServerManager when singleton doesn't exist."""
        mock_server_manager.get_instance.return_value = None
        mock_plugin_instance = Mock()
        mock_plugin_manager.return_value = mock_plugin_instance
        mock_server_instance = Mock()
        mock_server_instance.servers = {}
        mock_server_instance._load_servers = Mock()
        mock_server_instance._load_routing_rules = Mock()
        mock_server_manager.return_value = mock_server_instance

        result = get_chat_service()

        mock_plugin_manager.assert_called_once()
        mock_plugin_instance.discover_plugins.assert_called_once()

    @patch("utils.llm_utils.ServerManager")
    def test_get_chat_service_returns_none_on_exception(self, mock_server_manager):
        """Returns None when exception occurs."""
        mock_server_manager.get_instance.side_effect = Exception("Test error")

        result = get_chat_service()

        assert result is None


class TestValidateLLMConfig:
    """Tests for validate_llm_config function."""

    @patch("utils.llm_utils.get_chat_service")
    def test_validate_llm_config_returns_true_with_valid_service(self, mock_get_service):
        """Returns True when ChatService is properly configured."""
        mock_service = Mock()
        mock_selection_service = Mock()
        mock_ability_service = Mock()
        mock_ability_service.get_ability_instances_by_type.return_value = [Mock()]
        mock_selection_service._ability_service = mock_ability_service
        mock_service.selection_service = mock_selection_service
        mock_get_service.return_value = mock_service

        result = validate_llm_config()

        assert result is True

    @patch("utils.llm_utils.get_chat_service")
    def test_validate_llm_config_returns_true_with_service_no_abilities(self, mock_get_service):
        """Returns True when ChatService exists even without abilities."""
        mock_service = Mock()
        mock_service.selection_service = None
        mock_get_service.return_value = mock_service

        result = validate_llm_config()

        assert result is True

    @patch("utils.llm_utils.get_chat_service")
    def test_validate_llm_config_returns_false_on_exception(self, mock_get_service):
        """Returns False when exception occurs."""
        mock_get_service.side_effect = Exception("Test error")

        result = validate_llm_config()

        assert result is False

    @patch("utils.llm_utils.get_chat_service")
    def test_validate_llm_config_returns_none_service(self, mock_get_service):
        """Returns False when get_chat_service returns None."""
        mock_get_service.return_value = None

        result = validate_llm_config()

        assert result is False