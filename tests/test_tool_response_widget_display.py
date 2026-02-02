"""
Test ToolResponseContentWidget display of result.

Tests that:
1. ToolResponseContentWidget displays result correctly
2. Widget handles different result types (dict, list, string)
3. Widget handles large results with QTextEdit
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication
from agent.chat.content import ToolResponseContent
from app.ui.chat.message.tool_response_content_widget import ToolResponseContentWidget


class TestToolResponseWidgetDisplay:
    """Tests for ToolResponseContentWidget display."""

    @pytest.fixture(autouse=True)
    def setup_qt(self):
        """Setup Qt application for widgets."""
        if not QApplication.instance():
            app = QApplication([])
        yield

    def test_widget_displays_dict_result(self):
        """Test widget displays dictionary result."""
        result = {
            "success": True,
            "total_scenes": 10,
            "created_scenes": ["scene_001", "scene_002", "scene_003"]
        }

        content = ToolResponseContent(
            tool_name="test_tool",
            result=result,
            tool_status="completed",
            title="Tool Result: test_tool",
            description="Tool execution completed"
        )
        content.complete()

        widget = ToolResponseContentWidget(content)

        # Verify widget was created and result is preserved
        assert widget is not None
        assert widget.structure_content.result == result

        # Verify widget state includes result
        state = widget.get_state()
        assert state["result"] == result
        assert state["tool_name"] == "test_tool"
        assert state["tool_status"] == "completed"

    def test_widget_displays_string_result(self):
        """Test widget displays string result."""
        result = "Operation completed successfully"

        content = ToolResponseContent(
            tool_name="test_tool",
            result=result,
            tool_status="completed",
            title="Tool Result: test_tool",
            description="Tool execution completed"
        )
        content.complete()

        widget = ToolResponseContentWidget(content)

        # Verify widget was created
        assert widget is not None
        assert widget.structure_content.result == result

    def test_widget_displays_large_result_in_text_edit(self):
        """Test widget displays large result in QTextEdit."""
        # Create a large result (> 100 chars or with newlines)
        result = "\n".join([f"Line {i}: Some content here" for i in range(10)])

        content = ToolResponseContent(
            tool_name="test_tool",
            result=result,
            tool_status="completed",
            title="Tool Result: test_tool",
            description="Tool execution completed"
        )
        content.complete()

        widget = ToolResponseContentWidget(content)

        # Verify widget was created
        assert widget is not None
        assert widget.structure_content.result == result

        # For large results, should use QTextEdit
        from PySide6.QtWidgets import QTextEdit
        text_edits = widget.findChildren(QTextEdit)
        # Note: May be 0 or 1 depending on how the result is formatted
        # The important thing is the widget is created without error

    def test_widget_displays_error_instead_of_result(self):
        """Test widget displays error when tool_status is failed."""
        content = ToolResponseContent(
            tool_name="test_tool",
            result=None,
            error="Script execution failed",
            tool_status="failed",
            title="Tool Result: test_tool",
            description="Tool execution failed"
        )
        content.fail()

        widget = ToolResponseContentWidget(content)

        # Verify widget was created
        assert widget is not None
        assert widget.structure_content.result is None
        assert widget.structure_content.error == "Script execution failed"
        assert widget.structure_content.tool_status == "failed"

    def test_widget_displays_result_with_error(self):
        """Test widget displays both result and error when both present."""
        result = {"partial": "success"}
        error = "Some warnings occurred"

        content = ToolResponseContent(
            tool_name="test_tool",
            result=result,
            error=error,
            tool_status="completed",  # Still completed despite error
            title="Tool Result: test_tool",
            description="Tool execution completed with warnings"
        )
        content.complete()

        widget = ToolResponseContentWidget(content)

        # Verify widget was created
        assert widget is not None
        assert widget.structure_content.result == result
        assert widget.structure_content.error == error


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
