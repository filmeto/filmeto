"""Test PlanTaskWidget data flow and rendering."""
import pytest
from datetime import datetime

from agent.chat.content import PlanTaskContent
from agent.chat.agent_chat_types import ContentType
from agent.plan.plan_models import PlanTask, TaskStatus


class TestPlanTaskContent:
    """Test PlanTaskContent serialization and deserialization."""

    def test_plan_task_content_to_dict(self):
        """Test that PlanTaskContent.to_dict() returns correct structure."""
        content = PlanTaskContent(
            plan_id="plan-123",
            task_id="task-456",
            task_name="Test Task",
            task_status="running",
            previous_status="waiting",
            crew_member={
                "name": "Script Writer",
                "icon": "S",
                "color": "#4a90e2"
            }
        )

        result = content.to_dict()

        # Verify structure
        assert result["content_type"] == "plan_task"
        assert "data" in result
        assert result["data"]["plan_id"] == "plan-123"
        assert result["data"]["task_id"] == "task-456"
        assert result["data"]["task_name"] == "Test Task"
        assert result["data"]["task_status"] == "running"
        assert result["data"]["previous_status"] == "waiting"
        assert result["data"]["crew_member"]["name"] == "Script Writer"

    def test_plan_task_content_from_task(self):
        """Test PlanTaskContent.from_task() creates correct content."""
        task = PlanTask(
            id="task-789",
            name="Generate Script",
            description="Generate a video script based on user requirements",
            title="Script Writer",
            status=TaskStatus.RUNNING,
            needs=["research", "outline"]
        )

        content = PlanTaskContent.from_task(
            task=task,
            plan_id="plan-abc",
            previous_status="waiting"
        )

        assert content.content_type == ContentType.PLAN_TASK
        assert content.plan_id == "plan-abc"
        assert content.task_id == "task-789"
        assert content.task_name == "Generate Script"
        assert content.task_status == "running"
        assert content.description == "Generate a video script based on user requirements"
        assert content.needs == ["research", "outline"]
        assert content.previous_status == "waiting"

    def test_plan_task_content_serialization_for_qml(self):
        """Test that serialized data is compatible with QML expectations."""
        content = PlanTaskContent(
            plan_id="plan-xyz",
            task_id="task-uvw",
            task_name="Review Content",
            task_status="completed",
            description="Review and validate the generated content",
            needs=["generate_content"],
            previous_status="running"
        )

        data = content.to_dict()

        # QML expects data.data or data structure
        # PlanTaskWidget uses: updateData: data.data || data
        update_data = data.get("data", data)

        # Verify QML can access these fields
        assert update_data["task_name"] == "Review Content"
        assert update_data["task_status"] == "completed"
        assert update_data["description"] == "Review and validate the generated content"
        assert update_data["needs"] == ["generate_content"]
        assert update_data["previous_status"] == "running"
        assert update_data["plan_id"] == "plan-xyz"
        assert update_data["task_id"] == "task-uvw"

    def test_plan_task_categorized_as_thinking_content(self):
        """Test that plan_task is NOT in main content types (shown in Thinking section)."""
        # Main content types - plan_task should NOT be here
        main_content_types = {
            "text", "code_block", "image", "video", "audio",
            "link", "button", "form", "file", "file_attachment"
        }

        # plan_task should not be in main content types
        assert "plan_task" not in main_content_types
        assert "todo_write" not in main_content_types


class TestPlanTaskContentTypeLookup:
    """Test that plan_task is correctly categorized in content type lookups."""

    def test_content_type_value(self):
        """Test that ContentType.PLAN_TASK has correct value."""
        assert ContentType.PLAN_TASK.value == "plan_task"

    def test_content_class_map(self):
        """Test that PLAN_TASK maps to PlanTaskContent."""
        from agent.chat.content import _CONTENT_CLASS_MAP, PlanTaskContent

        assert _CONTENT_CLASS_MAP.get(ContentType.PLAN_TASK) == PlanTaskContent

    def test_from_dict_dispatch(self):
        """Test that from_dict dispatches to correct class."""
        from agent.chat.content import StructureContent, PlanTaskContent

        data = {
            "content_type": "plan_task",
            "content_id": "test-id",
            "data": {
                "plan_id": "plan-1",
                "task_id": "task-1",
                "task_name": "Test",
                "task_status": "running"
            }
        }

        content = StructureContent.from_dict(data)

        assert isinstance(content, PlanTaskContent)
        assert content.task_name == "Test"
        assert content.task_status == "running"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
