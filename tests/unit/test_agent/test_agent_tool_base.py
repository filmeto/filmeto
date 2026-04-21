"""
Unit tests for agent/tool/ module.

Tests for:
- agent/tool/base_tool.py - ToolParameter, ToolMetadata dataclasses
- agent/tool/tool_context.py - ToolContext class
- agent/tool/tool_service.py - ToolService registration
- agent/tool/__init__.py - Module exports
"""
import pytest
from typing import Dict, Any, Optional

from agent.tool.base_tool import ToolParameter, ToolMetadata, BaseTool
from agent.tool.tool_context import ToolContext
from agent.tool.tool_service import ToolService


class TestToolParameter:
    """Tests for ToolParameter dataclass"""

    def test_tool_parameter_creation_basic(self):
        """ToolParameter should be created with basic fields"""
        param = ToolParameter(
            name="input_file",
            description="Path to input file",
            param_type="string"
        )
        assert param.name == "input_file"
        assert param.description == "Path to input file"
        assert param.param_type == "string"
        assert param.required is False
        assert param.default is None

    def test_tool_parameter_required(self):
        """ToolParameter should accept required flag"""
        param = ToolParameter(
            name="output_file",
            description="Output path",
            param_type="string",
            required=True
        )
        assert param.required is True

    def test_tool_parameter_with_default(self):
        """ToolParameter should accept default value"""
        param = ToolParameter(
            name="count",
            description="Number of items",
            param_type="number",
            default=10
        )
        assert param.default == 10

    def test_tool_parameter_to_dict(self):
        """ToolParameter.to_dict should return proper dict"""
        param = ToolParameter(
            name="test",
            description="Test param",
            param_type="boolean",
            required=True
        )
        data = param.to_dict()
        assert data["name"] == "test"
        assert data["description"] == "Test param"
        assert data["type"] == "boolean"
        assert data["required"] is True

    def test_tool_parameter_to_dict_with_default(self):
        """ToolParameter.to_dict should include default"""
        param = ToolParameter(
            name="test",
            description="Test",
            param_type="number",
            default=5
        )
        data = param.to_dict()
        assert "default" in data
        assert data["default"] == 5


class TestToolMetadata:
    """Tests for ToolMetadata dataclass"""

    def test_tool_metadata_creation_basic(self):
        """ToolMetadata should be created with basic fields"""
        meta = ToolMetadata(
            name="test_tool",
            description="A test tool"
        )
        assert meta.name == "test_tool"
        assert meta.description == "A test tool"
        assert meta.parameters == []
        assert meta.return_description == ""

    def test_tool_metadata_with_parameters(self):
        """ToolMetadata should accept parameters"""
        params = [
            ToolParameter(name="arg1", description="First arg", param_type="string"),
            ToolParameter(name="arg2", description="Second arg", param_type="number")
        ]
        meta = ToolMetadata(
            name="complex_tool",
            description="Complex tool",
            parameters=params,
            return_description="Result object"
        )
        assert len(meta.parameters) == 2
        assert meta.return_description == "Result object"

    def test_tool_metadata_to_dict(self):
        """ToolMetadata.to_dict should return proper dict"""
        meta = ToolMetadata(
            name="test",
            description="Test tool",
            return_description="Result"
        )
        data = meta.to_dict()
        assert data["name"] == "test"
        assert data["description"] == "Test tool"
        assert data["parameters"] == []
        assert data["return_description"] == "Result"

    def test_tool_metadata_to_dict_with_parameters(self):
        """ToolMetadata.to_dict should include parameters"""
        params = [
            ToolParameter(name="arg1", description="Arg", param_type="string")
        ]
        meta = ToolMetadata(name="test", description="Test", parameters=params)
        data = meta.to_dict()
        assert len(data["parameters"]) == 1


class TestToolContext:
    """Tests for ToolContext class"""

    def test_tool_context_creation_empty(self):
        """ToolContext should be created with defaults"""
        context = ToolContext()
        assert context.workspace is None
        assert context.project is None
        assert context.project_name is None
        assert context.llm_service is None

    def test_tool_context_creation_with_args(self):
        """ToolContext should accept all arguments"""
        context = ToolContext(
            workspace=None,
            project=None,
            project_name="test_project",
            llm_service=None,
            custom_key="custom_value"
        )
        assert context.project_name == "test_project"
        assert context.get("custom_key") == "custom_value"

    def test_tool_context_get_set(self):
        """ToolContext.get and set should work"""
        context = ToolContext()
        context.set("test_key", "test_value")
        assert context.get("test_key") == "test_value"
        assert context.get("nonexistent", "default") == "default"

    def test_tool_context_update(self):
        """ToolContext.update should work"""
        context = ToolContext()
        context.update({"key1": "val1", "key2": "val2"})
        assert context.get("key1") == "val1"
        assert context.get("key2") == "val2"

    def test_tool_context_to_dict(self):
        """ToolContext.to_dict should return proper dict"""
        context = ToolContext(project_name="test")
        data = context.to_dict()
        assert "workspace" in data
        assert "project" in data
        assert "project_name" in data
        assert data["project_name"] == "test"

    def test_tool_context_from_dict(self):
        """ToolContext.from_dict should create context"""
        data = {
            "project_name": "test_project",
            "custom_data": "custom_value"
        }
        context = ToolContext.from_dict(data)
        assert context.project_name == "test_project"
        assert context.get("custom_data") == "custom_value"

    def test_tool_context_properties(self):
        """ToolContext properties should work"""
        context = ToolContext()
        # Set via properties
        context.project_name = "new_project"
        assert context.project_name == "new_project"

    def test_tool_context_get_screenplay_manager_none(self):
        """ToolContext.get_screenplay_manager should return None without project"""
        context = ToolContext()
        result = context.get_screenplay_manager()
        assert result is None

    def test_tool_context_get_project_path_none(self):
        """ToolContext.get_project_path should return None without project"""
        context = ToolContext()
        result = context.get_project_path()
        assert result is None

    def test_tool_context_get_skill_knowledge_none(self):
        """ToolContext.get_skill_knowledge should return None"""
        context = ToolContext()
        result = context.get_skill_knowledge()
        assert result is None

    def test_tool_context_get_skill_description_none(self):
        """ToolContext.get_skill_description should return None"""
        context = ToolContext()
        result = context.get_skill_description()
        assert result is None

    def test_tool_context_repr(self):
        """ToolContext.__repr__ should return readable string"""
        context = ToolContext(project_name="test")
        repr_str = repr(context)
        assert "ToolContext" in repr_str
        assert "test" in repr_str


class TestToolService:
    """Tests for ToolService"""

    def test_tool_service_creation(self):
        """ToolService should be instantiable"""
        service = ToolService()
        assert service is not None

    def test_tool_service_tools_dict(self):
        """ToolService should have tools dict"""
        service = ToolService()
        assert hasattr(service, 'tools')
        assert isinstance(service.tools, dict)

    def test_tool_service_get_available_tools(self):
        """ToolService.get_available_tools should return list"""
        service = ToolService()
        tools = service.get_available_tools()
        assert isinstance(tools, list)

    def test_tool_service_register_tool(self):
        """ToolService.register_tool should work"""
        service = ToolService()
        # Create a mock tool
        class MockTool(BaseTool):
            async def execute(self, **kwargs):
                pass
        tool = MockTool(name="mock_tool", description="A mock tool")
        service.register_tool(tool)
        assert "mock_tool" in service.tools

    def test_tool_service_get_tool_metadata_not_found_raises(self):
        """ToolService.get_tool_metadata should raise for unknown tool"""
        service = ToolService()
        with pytest.raises(ValueError):
            service.get_tool_metadata("nonexistent_tool_xyz")

    def test_tool_service_get_all_tools_metadata(self):
        """ToolService.get_all_tools_metadata should return list"""
        service = ToolService()
        metadata = service.get_all_tools_metadata()
        assert isinstance(metadata, list)


class TestToolInitExports:
    """Tests for agent/tool/__init__.py exports"""

    def test_tool_service_exported(self):
        """ToolService should be exported from tool package"""
        from agent.tool import ToolService
        assert ToolService is not None

    def test_base_tool_exported(self):
        """BaseTool should be exported from tool package"""
        from agent.tool import BaseTool
        assert BaseTool is not None

    def test_tool_context_exported(self):
        """ToolContext should be exported from tool package"""
        from agent.tool import ToolContext
        assert ToolContext is not None

    def test_tool_parameter_exported(self):
        """ToolParameter should be exported"""
        from agent.tool import ToolParameter
        assert ToolParameter is not None

    def test_tool_metadata_exported(self):
        """ToolMetadata should be exported"""
        from agent.tool import ToolMetadata
        assert ToolMetadata is not None