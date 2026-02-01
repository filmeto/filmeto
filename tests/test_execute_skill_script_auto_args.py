"""
Test ExecuteSkillScriptTool automatic argument injection.

Tests that:
1. project-path is automatically added from context
2. workspace is automatically added from context
3. User-provided arguments are not overridden
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.tool.system.execute_skill_script import ExecuteSkillScriptTool
from agent.tool.tool_context import ToolContext
from unittest.mock import Mock, MagicMock, patch


class MockProject:
    """Mock project object."""
    def __init__(self, project_path="/test/project"):
        self.project_path = project_path
        self.project_name = "test_project"


class MockWorkspace:
    """Mock workspace object."""
    def __init__(self, workspace_path="/test/workspace"):
        self.workspace_path = workspace_path


class TestExecuteSkillScriptAutoArgs:
    """Tests for automatic argument injection in ExecuteSkillScriptTool."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return ExecuteSkillScriptTool()

    @pytest.fixture
    def mock_context(self):
        """Create mock ToolContext with project and workspace."""
        context = Mock(spec=ToolContext)
        context.project = MockProject("/test/project/path")
        context.workspace = MockWorkspace("/test/workspace/path")
        return context

    @pytest.mark.asyncio
    async def test_auto_add_project_path_from_context(self, tool, mock_context):
        """Test that project-path is automatically added from context."""
        parameters = {
            "script_path": "/test/script.py",
            "args": {"concept": "test concept"}
        }

        captured_argv = []

        async def mock_execute_script(script_path, argv, context, **kwargs):
            captured_argv.extend(argv)
            return {"status": "success", "output": "test output"}

        # Mock os.path.exists to make the script appear to exist
        with patch('os.path.exists', return_value=True), \
             patch('agent.tool.tool_service.ToolService') as MockToolService:
            mock_instance = MagicMock()
            mock_instance.execute_script = mock_execute_script
            MockToolService.return_value = mock_instance

            events = []
            async for event in tool.execute(
                parameters=parameters,
                context=mock_context,
                project_name="test_project",
                react_type="test_react",
                run_id="test_run",
                step_id=0,
            ):
                events.append(event)
                if len(events) > 5:
                    break

            assert "--project-path" in captured_argv
            project_path_idx = captured_argv.index("--project-path")
            assert captured_argv[project_path_idx + 1] == "/test/project/path"
            assert "--concept" in captured_argv
            concept_idx = captured_argv.index("--concept")
            assert captured_argv[concept_idx + 1] == "test concept"

    @pytest.mark.asyncio
    async def test_auto_add_workspace_from_context(self, tool, mock_context):
        """Test that workspace is automatically added from context."""
        parameters = {
            "script_path": "/test/script.py",
            "args": {"concept": "test concept"}
        }

        captured_argv = []

        async def mock_execute_script(script_path, argv, context, **kwargs):
            captured_argv.extend(argv)
            return {"status": "success", "output": "test output"}

        with patch('os.path.exists', return_value=True), \
             patch('agent.tool.tool_service.ToolService') as MockToolService:
            mock_instance = MagicMock()
            mock_instance.execute_script = mock_execute_script
            MockToolService.return_value = mock_instance

            events = []
            async for event in tool.execute(
                parameters=parameters,
                context=mock_context,
                project_name="test_project",
                react_type="test_react",
                run_id="test_run",
                step_id=0,
            ):
                events.append(event)
                if len(events) > 5:
                    break

            assert "--workspace" in captured_argv
            workspace_idx = captured_argv.index("--workspace")
            assert captured_argv[workspace_idx + 1] == "/test/workspace/path"

    @pytest.mark.asyncio
    async def test_user_provided_project_path_not_overridden(self, tool, mock_context):
        """Test that user-provided project-path is not overridden."""
        parameters = {
            "script_path": "/test/script.py",
            "args": {
                "concept": "test concept",
                "project-path": "/user/project/path"
            }
        }

        captured_argv = []

        async def mock_execute_script(script_path, argv, context, **kwargs):
            captured_argv.extend(argv)
            return {"status": "success", "output": "test output"}

        with patch('os.path.exists', return_value=True), \
             patch('agent.tool.tool_service.ToolService') as MockToolService:
            mock_instance = MagicMock()
            mock_instance.execute_script = mock_execute_script
            MockToolService.return_value = mock_instance

            events = []
            async for event in tool.execute(
                parameters=parameters,
                context=mock_context,
                project_name="test_project",
                react_type="test_react",
                run_id="test_run",
                step_id=0,
            ):
                events.append(event)
                if len(events) > 5:
                    break

            project_path_indices = [i for i, arg in enumerate(captured_argv) if arg == "--project-path"]
            assert len(project_path_indices) == 1
            project_path_idx = project_path_indices[0]
            assert captured_argv[project_path_idx + 1] == "/user/project/path"

    @pytest.mark.asyncio
    async def test_no_auto_args_when_context_none(self, tool):
        """Test that no auto args are added when context is None."""
        parameters = {
            "script_path": "/test/script.py",
            "args": {"concept": "test concept"}
        }

        captured_argv = []

        async def mock_execute_script(script_path, argv, context, **kwargs):
            captured_argv.extend(argv)
            return {"status": "success", "output": "test output"}

        with patch('os.path.exists', return_value=True), \
             patch('agent.tool.tool_service.ToolService') as MockToolService:
            mock_instance = MagicMock()
            mock_instance.execute_script = mock_execute_script
            MockToolService.return_value = mock_instance

            events = []
            async for event in tool.execute(
                parameters=parameters,
                context=None,
                project_name="test_project",
                react_type="test_react",
                run_id="test_run",
                step_id=0,
            ):
                events.append(event)
                if len(events) > 5:
                    break

            assert "--project-path" not in captured_argv
            assert "--workspace" not in captured_argv
            assert "--concept" in captured_argv

    @pytest.mark.asyncio
    async def test_no_auto_args_when_context_project_none(self, tool):
        """Test that no auto args are added when context.project is None."""
        parameters = {
            "script_path": "/test/script.py",
            "args": {"concept": "test concept"}
        }

        captured_argv = []

        async def mock_execute_script(script_path, argv, context, **kwargs):
            captured_argv.extend(argv)
            return {"status": "success", "output": "test output"}

        with patch('os.path.exists', return_value=True), \
             patch('agent.tool.tool_service.ToolService') as MockToolService:
            mock_instance = MagicMock()
            mock_instance.execute_script = mock_execute_script
            MockToolService.return_value = mock_instance

            context = Mock(spec=ToolContext)
            context.project = None
            context.workspace = None

            events = []
            async for event in tool.execute(
                parameters=parameters,
                context=context,
                project_name="test_project",
                react_type="test_react",
                run_id="test_run",
                step_id=0,
            ):
                events.append(event)
                if len(events) > 5:
                    break

            assert "--project-path" not in captured_argv
            assert "--workspace" not in captured_argv


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
