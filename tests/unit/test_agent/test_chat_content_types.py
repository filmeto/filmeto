"""
Unit tests for agent chat content types.

Tests for:
- agent/chat/agent_chat_message.py
- agent/chat/agent_chat_signals.py
- agent/chat/content/button_content.py
- agent/chat/content/code_content.py
- agent/chat/content/content_status.py
- agent/chat/content/crew_member_activity_content.py
- agent/chat/content/crew_member_read_content.py
- agent/chat/content/data_content.py
- agent/chat/content/error_content.py
- agent/chat/content/file_content.py
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_types import ContentType, DisplayCategory
from agent.chat.content.content_status import ContentStatus
from agent.chat.content.button_content import ButtonContent
from agent.chat.content.code_content import CodeBlockContent
from agent.chat.content.crew_member_activity_content import CrewMemberActivityContent
from agent.chat.content.crew_member_read_content import CrewMemberReadContent
from agent.chat.content.data_content import TableContent, ChartContent
from agent.chat.content.error_content import ErrorContent
from agent.chat.content.file_content import FileAttachmentContent


class TestContentStatus:
    """Tests for ContentStatus enum"""

    def test_all_status_values(self):
        """Verify all status values are defined"""
        assert ContentStatus.CREATING.value == "creating"
        assert ContentStatus.UPDATING.value == "updating"
        assert ContentStatus.COMPLETED.value == "completed"
        assert ContentStatus.FAILED.value == "failed"

    def test_status_is_string_enum(self):
        """Verify ContentStatus is a string enum"""
        assert ContentStatus("creating") == ContentStatus.CREATING
        assert ContentStatus("completed") == ContentStatus.COMPLETED


class TestAgentMessage:
    """Tests for AgentMessage dataclass"""

    def test_message_defaults(self):
        """Verify default values are set correctly"""
        msg = AgentMessage(sender_id="test_sender")
        assert msg.sender_id == "test_sender"
        assert msg.sender_name == ""
        assert msg.message_id != ""  # Should auto-generate UUID
        assert isinstance(msg.timestamp, datetime)
        assert msg.metadata == {}
        assert msg.structured_content == []

    def test_message_with_content(self):
        """Verify message can hold structured content"""
        content = ButtonContent(
            content_type=ContentType.BUTTON,
            label="Click Me"
        )
        msg = AgentMessage(
            sender_id="sender",
            sender_name="Test Agent",
            structured_content=[content]
        )
        assert len(msg.structured_content) == 1
        assert msg.structured_content[0].label == "Click Me"

    def test_message_id_unique(self):
        """Verify each message gets a unique ID"""
        msg1 = AgentMessage(sender_id="a")
        msg2 = AgentMessage(sender_id="b")
        assert msg1.message_id != msg2.message_id


class TestButtonContent:
    """Tests for ButtonContent"""

    def test_button_defaults(self):
        """Verify default values"""
        btn = ButtonContent(content_type=ContentType.BUTTON)
        assert btn.content_type == ContentType.BUTTON
        assert btn.label == ""
        assert btn.action == ""
        assert btn.button_style == "primary"
        assert btn.disabled == False
        assert btn.payload is None

    def test_button_to_dict(self):
        """Verify to_dict serialization"""
        btn = ButtonContent(
            content_type=ContentType.BUTTON,
            label="Submit",
            action="submit_form",
            button_style="success",
            payload={"form_id": "123"}
        )
        result = btn.to_dict()
        assert result["content_type"] == "button"
        assert result["data"]["label"] == "Submit"
        assert result["data"]["action"] == "submit_form"
        assert result["data"]["style"] == "success"
        assert result["data"]["payload"]["form_id"] == "123"

    def test_button_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "button",
            "title": "Action Button",
            "data": {
                "label": "Click",
                "action": "click_action",
                "style": "danger",
                "disabled": True
            }
        }
        btn = ButtonContent.from_dict(data)
        assert btn.label == "Click"
        assert btn.action == "click_action"
        assert btn.button_style == "danger"
        assert btn.disabled == True

    def test_button_display_category(self):
        """Verify button is main content"""
        btn = ButtonContent(content_type=ContentType.BUTTON)
        assert btn.get_display_category() == DisplayCategory.MAIN
        assert btn.is_main_content() == True


class TestCodeBlockContent:
    """Tests for CodeBlockContent"""

    def test_code_defaults(self):
        """Verify default values"""
        code = CodeBlockContent(content_type=ContentType.CODE_BLOCK)
        assert code.content_type == ContentType.CODE_BLOCK
        assert code.code == ""
        assert code.language == "python"
        assert code.filename is None

    def test_code_to_dict(self):
        """Verify to_dict serialization"""
        code = CodeBlockContent(
            content_type=ContentType.CODE_BLOCK,
            code="print('hello')",
            language="python",
            filename="test.py"
        )
        result = code.to_dict()
        assert result["data"]["code"] == "print('hello')"
        assert result["data"]["language"] == "python"
        assert result["data"]["filename"] == "test.py"

    def test_code_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "code_block",
            "data": {
                "code": "def foo():",
                "language": "javascript",
                "filename": "app.js"
            }
        }
        code = CodeBlockContent.from_dict(data)
        assert code.code == "def foo():"
        assert code.language == "javascript"
        assert code.filename == "app.js"

    def test_code_is_main_content(self):
        """Verify code block is main content"""
        code = CodeBlockContent(content_type=ContentType.CODE_BLOCK)
        assert code.is_main_content() == True


class TestCrewMemberActivityContent:
    """Tests for CrewMemberActivityContent"""

    def test_activity_defaults(self):
        """Verify default values"""
        activity = CrewMemberActivityContent()
        assert activity.content_type == ContentType.CREW_MEMBER_ACTIVITY
        assert activity.crew_members == []

    def test_activity_to_dict(self):
        """Verify to_dict serialization"""
        activity = CrewMemberActivityContent(
            crew_members=[{"name": "Writer", "active": True}]
        )
        result = activity.to_dict()
        assert result["data"]["crew_members"] == [{"name": "Writer", "active": True}]

    def test_activity_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "crew_member_activity",
            "data": {
                "crew_members": [{"name": "Director", "active": False}]
            }
        }
        activity = CrewMemberActivityContent.from_dict(data)
        assert len(activity.crew_members) == 1
        assert activity.crew_members[0]["name"] == "Director"

    def test_activity_handles_invalid_crew_members(self):
        """Verify invalid crew_members is handled"""
        data = {
            "content_type": "crew_member_activity",
            "data": {"crew_members": "invalid"}
        }
        activity = CrewMemberActivityContent.from_dict(data)
        assert activity.crew_members == []

    def test_activity_is_auxiliary_content(self):
        """Verify activity is auxiliary content"""
        activity = CrewMemberActivityContent()
        assert activity.is_auxiliary_content() == True


class TestCrewMemberReadContent:
    """Tests for CrewMemberReadContent"""

    def test_read_defaults(self):
        """Verify default values"""
        read = CrewMemberReadContent()
        assert read.content_type == ContentType.CREW_MEMBER_READ
        assert read.crew_members == []

    def test_read_to_dict(self):
        """Verify to_dict serialization"""
        read = CrewMemberReadContent(
            crew_members=[{"name": "Editor", "read": True}]
        )
        result = read.to_dict()
        assert result["data"]["crew_members"] == [{"name": "Editor", "read": True}]

    def test_read_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "crew_member_read",
            "data": {
                "crew_members": [{"name": "Producer", "read": False}]
            }
        }
        read = CrewMemberReadContent.from_dict(data)
        assert len(read.crew_members) == 1
        assert read.crew_members[0]["name"] == "Producer"

    def test_read_handles_invalid_crew_members(self):
        """Verify invalid crew_members is handled"""
        data = {
            "content_type": "crew_member_read",
            "data": {"crew_members": None}
        }
        read = CrewMemberReadContent.from_dict(data)
        assert read.crew_members == []


class TestTableContent:
    """Tests for TableContent"""

    def test_table_defaults(self):
        """Verify default values"""
        table = TableContent(content_type=ContentType.TABLE)
        assert table.content_type == ContentType.TABLE
        assert table.headers == []
        assert table.rows == []
        assert table.table_title is None

    def test_table_to_dict(self):
        """Verify to_dict serialization"""
        table = TableContent(
            content_type=ContentType.TABLE,
            headers=["Name", "Age"],
            rows=[["Alice", "25"], ["Bob", "30"]],
            table_title="Users"
        )
        result = table.to_dict()
        assert result["data"]["headers"] == ["Name", "Age"]
        assert result["data"]["rows"] == [["Alice", "25"], ["Bob", "30"]]
        assert result["data"]["title"] == "Users"

    def test_table_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "table",
            "data": {
                "headers": ["A", "B"],
                "rows": [["1", "2"]],
                "title": "Data"
            }
        }
        table = TableContent.from_dict(data)
        assert table.headers == ["A", "B"]
        assert table.rows == [["1", "2"]]
        assert table.table_title == "Data"


class TestChartContent:
    """Tests for ChartContent"""

    def test_chart_defaults(self):
        """Verify default values"""
        chart = ChartContent(content_type=ContentType.CHART)
        assert chart.content_type == ContentType.CHART
        assert chart.chart_type == ""
        assert chart.data == {}
        assert chart.chart_title is None

    def test_chart_to_dict(self):
        """Verify to_dict serialization"""
        chart = ChartContent(
            content_type=ContentType.CHART,
            chart_type="bar",
            data={"values": [10, 20, 30]},
            chart_title="Sales",
            x_axis_label="Month",
            y_axis_label="Amount"
        )
        result = chart.to_dict()
        assert result["data"]["chart_type"] == "bar"
        assert result["data"]["data"]["values"] == [10, 20, 30]
        assert result["data"]["title"] == "Sales"
        assert result["data"]["x_axis_label"] == "Month"

    def test_chart_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "chart",
            "data": {
                "chart_type": "pie",
                "data": {"slices": [1, 2]},
                "title": "Distribution"
            }
        }
        chart = ChartContent.from_dict(data)
        assert chart.chart_type == "pie"
        assert chart.data == {"slices": [1, 2]}
        assert chart.chart_title == "Distribution"


class TestErrorContent:
    """Tests for ErrorContent"""

    def test_error_defaults(self):
        """Verify default values"""
        err = ErrorContent(content_type=ContentType.ERROR)
        assert err.content_type == ContentType.ERROR
        assert err.error_message == ""
        assert err.error_type is None
        assert err.details is None

    def test_error_to_dict(self):
        """Verify to_dict serialization"""
        err = ErrorContent(
            content_type=ContentType.ERROR,
            error_message="Something went wrong",
            error_type="RuntimeError",
            details="Stack trace here"
        )
        result = err.to_dict()
        assert result["data"]["error"] == "Something went wrong"
        assert result["data"]["error_type"] == "RuntimeError"
        assert result["data"]["details"] == "Stack trace here"

    def test_error_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "error",
            "data": {
                "error": "File not found",
                "error_type": "FileNotFoundError"
            }
        }
        err = ErrorContent.from_dict(data)
        assert err.error_message == "File not found"
        assert err.error_type == "FileNotFoundError"

    def test_error_is_auxiliary_content(self):
        """Verify error is auxiliary content"""
        err = ErrorContent(content_type=ContentType.ERROR)
        assert err.is_auxiliary_content() == True


class TestFileAttachmentContent:
    """Tests for FileAttachmentContent"""

    def test_file_defaults(self):
        """Verify default values"""
        file = FileAttachmentContent(content_type=ContentType.FILE_ATTACHMENT)
        assert file.content_type == ContentType.FILE_ATTACHMENT
        assert file.filename == ""
        assert file.file_path is None
        assert file.file_size is None
        assert file.mime_type is None

    def test_file_to_dict(self):
        """Verify to_dict serialization"""
        file = FileAttachmentContent(
            content_type=ContentType.FILE_ATTACHMENT,
            filename="document.pdf",
            file_path="/path/to/file",
            file_size=1024,
            mime_type="application/pdf"
        )
        result = file.to_dict()
        assert result["data"]["filename"] == "document.pdf"
        assert result["data"]["file_path"] == "/path/to/file"
        assert result["data"]["file_size"] == 1024
        assert result["data"]["mime_type"] == "application/pdf"

    def test_file_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "file_attachment",
            "data": {
                "filename": "image.png",
                "file_path": "/images/image.png",
                "mime_type": "image/png"
            }
        }
        file = FileAttachmentContent.from_dict(data)
        assert file.filename == "image.png"
        assert file.file_path == "/images/image.png"
        assert file.mime_type == "image/png"

    def test_file_is_main_content(self):
        """Verify file attachment is main content"""
        file = FileAttachmentContent(content_type=ContentType.FILE_ATTACHMENT)
        assert file.is_main_content() == True


class TestContentTypeDisplayCategories:
    """Tests for ContentType display categories"""

    def test_main_content_types(self):
        """Verify content types that are main content"""
        main_types = [
            ContentType.TEXT,
            ContentType.CODE_BLOCK,
            ContentType.IMAGE,
            ContentType.VIDEO,
            ContentType.AUDIO,
            ContentType.LINK,
            ContentType.BUTTON,
            ContentType.FORM,
            ContentType.FILE_ATTACHMENT,
        ]
        for ct in main_types:
            assert ct.is_main_content() == True
            assert ct.is_auxiliary_content() == False

    def test_auxiliary_content_types(self):
        """Verify content types that are auxiliary content"""
        auxiliary_types = [
            ContentType.THINKING,
            ContentType.TOOL_CALL,
            ContentType.TOOL_RESPONSE,
            ContentType.TABLE,
            ContentType.CHART,
            ContentType.ERROR,
            ContentType.CREW_MEMBER_ACTIVITY,
            ContentType.CREW_MEMBER_READ,
        ]
        for ct in auxiliary_types:
            assert ct.is_auxiliary_content() == True
            assert ct.is_main_content() == False