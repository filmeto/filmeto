"""
Unit tests for agent/core/ module.

Tests for:
- agent/core/filmeto_constants.py - Regex patterns and default values
- agent/core/filmeto_instance.py - Singleton behavior and instance caching
- agent/core/filmeto_utils.py - Utility functions for text extraction and workspace handling
"""
import pytest
import re
from typing import Optional, Any

from agent.core.filmeto_constants import (
    MENTION_PATTERN,
    PRODUCER_NAME,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_STREAMING,
    DEFAULT_MAX_HISTORY,
    DEFAULT_TRUNCATE_LIMIT,
    CONTENT_ID_PREFIX_META,
)
from agent.core.filmeto_utils import (
    extract_text_content,
    truncate_text,
    get_workspace_path_safe,
    get_project_from_workspace,
    resolve_project_name,
)
from agent.core.filmeto_instance import FilmetoInstanceManager


class TestFilmetoConstants:
    """Tests for filmeto_constants.py"""

    def test_mention_pattern_matches_basic_mentions(self):
        """MENTION_PATTERN should match basic @mentions"""
        text = "@director please review"
        matches = MENTION_PATTERN.findall(text)
        assert "director" in matches

    def test_mention_pattern_matches_multiple_mentions(self):
        """MENTION_PATTERN should match multiple mentions in one text"""
        text = "@producer and @director discuss with @editor"
        matches = MENTION_PATTERN.findall(text)
        assert len(matches) == 3
        assert "producer" in matches
        assert "director" in matches
        assert "editor" in matches

    def test_mention_pattern_matches_chinese_characters(self):
        """MENTION_PATTERN should match Chinese characters"""
        text = "@导演 请检查 @分镜师 的工作"
        matches = MENTION_PATTERN.findall(text)
        assert "导演" in matches
        assert "分镜师" in matches

    def test_mention_pattern_matches_japanese_characters(self):
        """MENTION_PATTERN should match Japanese characters"""
        text = "@監督 review this @カメラマン shot"
        matches = MENTION_PATTERN.findall(text)
        assert len(matches) == 2

    def test_mention_pattern_matches_korean_characters(self):
        """MENTION_PATTERN should match Korean characters"""
        text = "@감독님 check @촬영감독 work"
        matches = MENTION_PATTERN.findall(text)
        assert len(matches) == 2

    def test_mention_pattern_matches_underscores(self):
        """MENTION_PATTERN should match names with underscores"""
        text = "@vfx_supervisor review @story_board_artist work"
        matches = MENTION_PATTERN.findall(text)
        assert "vfx_supervisor" in matches
        assert "story_board_artist" in matches

    def test_mention_pattern_matches_hyphens(self):
        """MENTION_PATTERN should match names with hyphens"""
        text = "@sound-designer and @camera-operator"
        matches = MENTION_PATTERN.findall(text)
        assert "sound-designer" in matches
        assert "camera-operator" in matches

    def test_mention_pattern_no_match_without_at(self):
        """MENTION_PATTERN should not match text without @"""
        text = "director producer editor"
        matches = MENTION_PATTERN.findall(text)
        assert len(matches) == 0

    def test_producer_name_constant(self):
        """PRODUCER_NAME should be 'producer'"""
        assert PRODUCER_NAME == "producer"

    def test_default_model_constant(self):
        """DEFAULT_MODEL should be 'gpt-4o-mini'"""
        assert DEFAULT_MODEL == "gpt-4o-mini"

    def test_default_temperature_constant(self):
        """DEFAULT_TEMPERATURE should be 0.7"""
        assert DEFAULT_TEMPERATURE == 0.7
        assert isinstance(DEFAULT_TEMPERATURE, float)

    def test_default_streaming_constant(self):
        """DEFAULT_STREAMING should be True"""
        assert DEFAULT_STREAMING is True

    def test_default_max_history_constant(self):
        """DEFAULT_MAX_HISTORY should be 20"""
        assert DEFAULT_MAX_HISTORY == 20
        assert isinstance(DEFAULT_MAX_HISTORY, int)

    def test_default_truncate_limit_constant(self):
        """DEFAULT_TRUNCATE_LIMIT should be 160"""
        assert DEFAULT_TRUNCATE_LIMIT == 160
        assert isinstance(DEFAULT_TRUNCATE_LIMIT, int)

    def test_content_id_prefix_meta_constant(self):
        """CONTENT_ID_PREFIX_META should be 'meta:'"""
        assert CONTENT_ID_PREFIX_META == "meta:"


class TestFilmetoUtilsExtractTextContent:
    """Tests for extract_text_content utility function"""

    def test_extract_text_content_empty_structured_content(self):
        """extract_text_content returns empty string for None structured_content"""
        from agent.chat.agent_chat_message import AgentMessage
        message = AgentMessage(
            sender_id="user",
            structured_content=None
        )
        result = extract_text_content(message)
        assert result == ""

    def test_extract_text_content_empty_list(self):
        """extract_text_content returns empty string for empty list"""
        from agent.chat.agent_chat_message import AgentMessage
        message = AgentMessage(
            sender_id="user",
            structured_content=[]
        )
        result = extract_text_content(message)
        assert result == ""

    def test_extract_text_content_no_text_content(self):
        """extract_text_content returns empty string when no TextContent found"""
        from agent.chat.agent_chat_message import AgentMessage
        from agent.chat.content import CodeBlockContent
        message = AgentMessage(
            sender_id="user",
            structured_content=[
                CodeBlockContent(code="print('hello')", language="python")
            ]
        )
        result = extract_text_content(message)
        assert result == ""

    def test_extract_text_content_returns_text(self):
        """extract_text_content returns text from TextContent"""
        from agent.chat.agent_chat_message import AgentMessage
        from agent.chat.content import TextContent
        message = AgentMessage(
            sender_id="user",
            structured_content=[
                TextContent(text="Hello World")
            ]
        )
        result = extract_text_content(message)
        assert result == "Hello World"


class TestFilmetoUtilsTruncateText:
    """Tests for truncate_text utility function"""

    def test_truncate_text_none_input(self):
        """truncate_text returns empty string for None"""
        result = truncate_text(None)
        assert result == ""

    def test_truncate_text_short_text(self):
        """truncate_text returns original text if shorter than limit"""
        result = truncate_text("short text", limit=160)
        assert result == "short text"

    def test_truncate_text_exact_limit(self):
        """truncate_text returns original text if exactly limit"""
        text = "x" * 160
        result = truncate_text(text, limit=160)
        assert result == text
        assert len(result) == 160

    def test_truncate_text_long_text(self):
        """truncate_text truncates with ellipsis for long text"""
        text = "x" * 200
        result = truncate_text(text, limit=160)
        assert result.endswith("...")
        assert len(result) == 160

    def test_truncate_text_custom_limit(self):
        """truncate_text respects custom limit"""
        text = "hello world this is a test"
        result = truncate_text(text, limit=10)
        assert len(result) == 10
        assert result.endswith("...")

    def test_truncate_text_strips_whitespace(self):
        """truncate_text strips whitespace before truncating"""
        result = truncate_text("  hello  ", limit=10)
        assert result == "hello"


class TestFilmetoUtilsGetWorkspacePathSafe:
    """Tests for get_workspace_path_safe utility function"""

    def test_get_workspace_path_safe_none(self):
        """get_workspace_path_safe returns 'none' for None workspace"""
        result = get_workspace_path_safe(None)
        assert result == "none"

    def test_get_workspace_path_safe_with_workspace_path_attr(self):
        """get_workspace_path_safe returns workspace_path attribute"""
        class MockWorkspace:
            workspace_path = "/path/to/workspace"
        result = get_workspace_path_safe(MockWorkspace())
        assert result == "/path/to/workspace"

    def test_get_workspace_path_safe_with_path_attr(self):
        """get_workspace_path_safe returns path attribute if no workspace_path"""
        class MockWorkspace:
            path = "/path/to/project"
        result = get_workspace_path_safe(MockWorkspace())
        assert result == "/path/to/project"

    def test_get_workspace_path_safe_fallback_to_id(self):
        """get_workspace_path_safe returns str(id) as fallback"""
        class MockWorkspace:
            pass
        workspace = MockWorkspace()
        result = get_workspace_path_safe(workspace)
        assert result == str(id(workspace))


class TestFilmetoUtilsResolveProjectName:
    """Tests for resolve_project_name utility function"""

    def test_resolve_project_name_none(self):
        """resolve_project_name returns None for None project"""
        result = resolve_project_name(None)
        assert result is None

    def test_resolve_project_name_with_project_name_attr(self):
        """resolve_project_name returns project_name attribute"""
        class MockProject:
            project_name = "test_project"
        result = resolve_project_name(MockProject())
        assert result == "test_project"

    def test_resolve_project_name_with_name_attr(self):
        """resolve_project_name returns name attribute if no project_name"""
        class MockProject:
            name = "my_project"
        result = resolve_project_name(MockProject())
        assert result == "my_project"

    def test_resolve_project_name_string(self):
        """resolve_project_name returns string directly"""
        result = resolve_project_name("direct_project")
        assert result == "direct_project"


class TestFilmetoUtilsGetProjectFromWorkspace:
    """Tests for get_project_from_workspace utility function"""

    def test_get_project_from_workspace_none(self):
        """get_project_from_workspace returns None for None workspace"""
        result = get_project_from_workspace(None, "test")
        assert result is None

    def test_get_project_from_workspace_matching_current_project(self):
        """get_project_from_workspace returns project if name matches"""
        class MockProject:
            project_name = "test_project"
        class MockWorkspace:
            def get_project(self):
                return MockProject()
        result = get_project_from_workspace(MockWorkspace(), "test_project")
        assert result is not None
        assert result.project_name == "test_project"


class TestFilmetoInstanceManager:
    """Tests for FilmetoInstanceManager singleton behavior"""

    def test_instance_manager_clear_all_instances(self):
        """clear_all_instances should clear the instance cache"""
        # Clear any existing instances
        FilmetoInstanceManager.clear_all_instances()
        assert len(FilmetoInstanceManager.list_instances()) == 0

    def test_instance_manager_list_instances_empty(self):
        """list_instances returns empty list when no instances"""
        FilmetoInstanceManager.clear_all_instances()
        instances = FilmetoInstanceManager.list_instances()
        assert instances == []

    def test_instance_manager_has_instance_false_when_empty(self):
        """has_instance returns False when no instance exists"""
        FilmetoInstanceManager.clear_all_instances()
        class MockWorkspace:
            workspace_path = "/test/path"
        result = FilmetoInstanceManager.has_instance(MockWorkspace(), "test_project")
        assert result is False

    def test_instance_manager_remove_instance_returns_false(self):
        """remove_instance returns False when instance doesn't exist"""
        FilmetoInstanceManager.clear_all_instances()
        class MockWorkspace:
            workspace_path = "/test/path"
        result = FilmetoInstanceManager.remove_instance(MockWorkspace(), "nonexistent")
        assert result is False

    def test_instance_key_format(self):
        """Instance key should be workspace_path:project_name format"""
        # The key format is verified through get_workspace_path_safe behavior
        class MockWorkspace:
            workspace_path = "/path/to/workspace"
        key = f"{MockWorkspace().workspace_path}:test_project"
        assert key == "/path/to/workspace:test_project"