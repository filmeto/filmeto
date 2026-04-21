"""
Unit tests for agent chat content types (part 2).

Tests for:
- agent/chat/content/form_content.py
- agent/chat/content/link_content.py
- agent/chat/content/llm_output_content.py
- agent/chat/content/media_content.py (ImageContent, VideoContent, AudioContent)
- agent/chat/content/metadata_content.py
- agent/chat/content/plan_content.py (PlanContent, PlanTaskContent, StepContent, TaskListContent)
- agent/chat/content/progress_content.py
- agent/chat/content/skill_content.py
- agent/chat/content/text_content.py
- agent/chat/content/thinking_content.py
- agent/chat/content/structure_content.py
"""
import pytest
from unittest.mock import Mock

from agent.chat.agent_chat_types import ContentType, DisplayCategory
from agent.chat.content.content_status import ContentStatus
from agent.chat.content.structure_content import StructureContent
from agent.chat.content.form_content import FormContent
from agent.chat.content.link_content import LinkContent
from agent.chat.content.llm_output_content import LlmOutputContent
from agent.chat.content.media_content import ImageContent, VideoContent, AudioContent
from agent.chat.content.metadata_content import MetadataContent
from agent.chat.content.plan_content import (
    PlanContent,
    PlanTaskContent,
    StepContent,
    TaskListContent,
    _TASK_STATUS_MAP,
    _PLAN_STATUS_MAP,
)
from agent.chat.content.progress_content import ProgressContent
from agent.chat.content.skill_content import SkillContent, SkillExecutionState
from agent.chat.content.text_content import TextContent
from agent.chat.content.thinking_content import ThinkingContent


class TestStructureContent:
    """Tests for StructureContent base class"""

    def test_structure_content_defaults(self):
        """Verify default values"""
        content = StructureContent(content_type=ContentType.TEXT)
        assert content.content_type == ContentType.TEXT
        assert content.title is None
        assert content.description is None
        assert content.metadata == {}
        assert content.content_id != ""  # Should auto-generate UUID
        assert content.status == ContentStatus.CREATING
        assert content.parent_id is None

    def test_to_dict(self):
        """Verify to_dict serialization"""
        content = StructureContent(
            content_type=ContentType.TEXT,
            title="Test Title",
            description="Test Description",
            metadata={"key": "value"},
            status=ContentStatus.COMPLETED,
            parent_id="parent-123"
        )
        result = content.to_dict()
        assert result["content_type"] == "text"
        assert result["title"] == "Test Title"
        assert result["description"] == "Test Description"
        assert result["metadata"]["key"] == "value"
        assert result["status"] == "completed"
        assert result["parent_id"] == "parent-123"

    def test_update_sets_updating_status(self):
        """Verify update() sets status to UPDATING"""
        content = StructureContent(content_type=ContentType.TEXT)
        content.update(title="New Title")
        assert content.status == ContentStatus.UPDATING
        assert content.title == "New Title"

    def test_complete_sets_completed_status(self):
        """Verify complete() sets status to COMPLETED"""
        content = StructureContent(content_type=ContentType.TEXT)
        content.complete()
        assert content.status == ContentStatus.COMPLETED

    def test_fail_sets_failed_status(self):
        """Verify fail() sets status to FAILED"""
        content = StructureContent(content_type=ContentType.TEXT)
        content.fail("Error occurred")
        assert content.status == ContentStatus.FAILED
        assert content.metadata["error"] == "Error occurred"


class TestFormContent:
    """Tests for FormContent"""

    def test_form_defaults(self):
        """Verify default values"""
        form = FormContent(content_type=ContentType.FORM)
        assert form.content_type == ContentType.FORM
        assert form.fields == []
        assert form.submit_action == ""
        assert form.submit_label == "Submit"
        assert form.form_title is None

    def test_form_to_dict(self):
        """Verify to_dict serialization"""
        form = FormContent(
            content_type=ContentType.FORM,
            fields=[{"name": "email", "type": "text"}],
            submit_action="submit_form",
            submit_label="Send",
            form_title="Contact Form"
        )
        result = form.to_dict()
        assert result["data"]["fields"] == [{"name": "email", "type": "text"}]
        assert result["data"]["submit_action"] == "submit_form"
        assert result["data"]["submit_label"] == "Send"
        assert result["data"]["title"] == "Contact Form"

    def test_form_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "form",
            "data": {
                "fields": [{"name": "name"}],
                "submit_action": "submit",
                "submit_label": "Go"
            }
        }
        form = FormContent.from_dict(data)
        assert len(form.fields) == 1
        assert form.submit_action == "submit"
        assert form.submit_label == "Go"

    def test_form_is_main_content(self):
        """Verify form is main content"""
        form = FormContent(content_type=ContentType.FORM)
        assert form.is_main_content() == True


class TestLinkContent:
    """Tests for LinkContent"""

    def test_link_defaults(self):
        """Verify default values"""
        link = LinkContent(content_type=ContentType.LINK)
        assert link.content_type == ContentType.LINK
        assert link.url == ""
        assert link.link_title is None
        assert link.description is None
        assert link.favicon_url is None

    def test_link_to_dict(self):
        """Verify to_dict serialization"""
        link = LinkContent(
            content_type=ContentType.LINK,
            url="https://example.com",
            link_title="Example Site",
            description="A sample website",
            favicon_url="https://example.com/favicon.ico"
        )
        result = link.to_dict()
        assert result["data"]["url"] == "https://example.com"
        assert result["data"]["title"] == "Example Site"
        assert result["data"]["description"] == "A sample website"
        assert result["data"]["favicon_url"] == "https://example.com/favicon.ico"

    def test_link_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "link",
            "data": {
                "url": "https://test.com",
                "title": "Test"
            }
        }
        link = LinkContent.from_dict(data)
        assert link.url == "https://test.com"
        assert link.link_title == "Test"

    def test_link_is_main_content(self):
        """Verify link is main content"""
        link = LinkContent(content_type=ContentType.LINK)
        assert link.is_main_content() == True


class TestLlmOutputContent:
    """Tests for LlmOutputContent"""

    def test_llm_output_defaults(self):
        """Verify default values"""
        llm = LlmOutputContent(content_type=ContentType.LLM_OUTPUT)
        assert llm.content_type == ContentType.LLM_OUTPUT
        assert llm.output == ""
        assert llm.filmeto_server is None
        assert llm.filmeto_model is None

    def test_llm_output_to_dict(self):
        """Verify to_dict serialization"""
        llm = LlmOutputContent(
            content_type=ContentType.LLM_OUTPUT,
            output="Generated text here",
            filmeto_server="openai-server",
            filmeto_model="gpt-4"
        )
        result = llm.to_dict()
        assert result["data"]["output"] == "Generated text here"
        assert result["data"]["filmeto_server"] == "openai-server"
        assert result["data"]["filmeto_model"] == "gpt-4"

    def test_llm_output_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "llm_output",
            "data": {
                "output": "Response text",
                "filmeto_server": "local"
            }
        }
        llm = LlmOutputContent.from_dict(data)
        assert llm.output == "Response text"
        assert llm.filmeto_server == "local"

    def test_llm_output_is_auxiliary_content(self):
        """Verify llm_output is auxiliary content"""
        llm = LlmOutputContent(content_type=ContentType.LLM_OUTPUT)
        assert llm.is_auxiliary_content() == True


class TestImageContent:
    """Tests for ImageContent"""

    def test_image_defaults(self):
        """Verify default values"""
        img = ImageContent(content_type=ContentType.IMAGE)
        assert img.content_type == ContentType.IMAGE
        assert img.url is None
        assert img.alt_text is None
        assert img.width is None
        assert img.height is None

    def test_image_to_dict(self):
        """Verify to_dict serialization"""
        img = ImageContent(
            content_type=ContentType.IMAGE,
            url="https://example.com/image.png",
            alt_text="Sample image",
            width=800,
            height=600
        )
        result = img.to_dict()
        assert result["data"]["url"] == "https://example.com/image.png"
        assert result["data"]["alt_text"] == "Sample image"
        assert result["data"]["width"] == 800
        assert result["data"]["height"] == 600

    def test_image_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "image",
            "data": {"url": "/path/to/img.jpg", "alt_text": "Photo"}
        }
        img = ImageContent.from_dict(data)
        assert img.url == "/path/to/img.jpg"
        assert img.alt_text == "Photo"

    def test_image_is_main_content(self):
        """Verify image is main content"""
        img = ImageContent(content_type=ContentType.IMAGE)
        assert img.is_main_content() == True


class TestVideoContent:
    """Tests for VideoContent"""

    def test_video_defaults(self):
        """Verify default values"""
        video = VideoContent(content_type=ContentType.VIDEO)
        assert video.content_type == ContentType.VIDEO
        assert video.url is None
        assert video.thumbnail_url is None
        assert video.duration is None

    def test_video_to_dict(self):
        """Verify to_dict serialization"""
        video = VideoContent(
            content_type=ContentType.VIDEO,
            url="https://example.com/video.mp4",
            thumbnail_url="https://example.com/thumb.jpg",
            duration=120
        )
        result = video.to_dict()
        assert result["data"]["url"] == "https://example.com/video.mp4"
        assert result["data"]["thumbnail_url"] == "https://example.com/thumb.jpg"
        assert result["data"]["duration"] == 120

    def test_video_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "video",
            "data": {"url": "/video.mp4", "duration": 60}
        }
        video = VideoContent.from_dict(data)
        assert video.url == "/video.mp4"
        assert video.duration == 60

    def test_video_is_main_content(self):
        """Verify video is main content"""
        video = VideoContent(content_type=ContentType.VIDEO)
        assert video.is_main_content() == True


class TestAudioContent:
    """Tests for AudioContent"""

    def test_audio_defaults(self):
        """Verify default values"""
        audio = AudioContent(content_type=ContentType.AUDIO)
        assert audio.content_type == ContentType.AUDIO
        assert audio.url is None
        assert audio.thumbnail_url is None
        assert audio.duration is None
        assert audio.transcript is None

    def test_audio_to_dict(self):
        """Verify to_dict serialization"""
        audio = AudioContent(
            content_type=ContentType.AUDIO,
            url="https://example.com/audio.mp3",
            duration=30,
            transcript="Hello world"
        )
        result = audio.to_dict()
        assert result["data"]["url"] == "https://example.com/audio.mp3"
        assert result["data"]["duration"] == 30
        assert result["data"]["transcript"] == "Hello world"

    def test_audio_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "audio",
            "data": {"url": "/audio.wav", "transcript": "Speech"}
        }
        audio = AudioContent.from_dict(data)
        assert audio.url == "/audio.wav"
        assert audio.transcript == "Speech"

    def test_audio_is_main_content(self):
        """Verify audio is main content"""
        audio = AudioContent(content_type=ContentType.AUDIO)
        assert audio.is_main_content() == True


class TestMetadataContent:
    """Tests for MetadataContent"""

    def test_metadata_defaults(self):
        """Verify default values"""
        meta = MetadataContent(content_type=ContentType.METADATA)
        assert meta.content_type == ContentType.METADATA
        assert meta.metadata_type == ""
        assert meta.metadata_data == {}

    def test_metadata_to_dict(self):
        """Verify to_dict serialization"""
        meta = MetadataContent(
            content_type=ContentType.METADATA,
            metadata_type="todo_update",
            metadata_data={"completed": ["task1"]}
        )
        result = meta.to_dict()
        assert result["data"]["metadata_type"] == "todo_update"
        assert result["data"]["data"]["completed"] == ["task1"]

    def test_metadata_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "metadata",
            "data": {
                "metadata_type": "task_status",
                "data": {"status": "running"}
            }
        }
        meta = MetadataContent.from_dict(data)
        assert meta.metadata_type == "task_status"
        assert meta.metadata_data["status"] == "running"

    def test_metadata_is_auxiliary_content(self):
        """Verify metadata is auxiliary content"""
        meta = MetadataContent(content_type=ContentType.METADATA)
        assert meta.is_auxiliary_content() == True


class TestPlanContent:
    """Tests for PlanContent"""

    def test_plan_defaults(self):
        """Verify default values"""
        plan = PlanContent(content_type=ContentType.PLAN)
        assert plan.content_type == ContentType.PLAN
        assert plan.plan_id == ""
        assert plan.project_name == ""
        assert plan.operation == "create"
        assert plan.steps == []
        assert plan.tasks == []
        assert plan.plan_status == "pending"

    def test_plan_to_dict(self):
        """Verify to_dict serialization"""
        plan = PlanContent(
            content_type=ContentType.PLAN,
            plan_id="plan-123",
            plan_title="My Plan",
            steps=[{"text": "Step 1", "status": "waiting"}],
            total_steps=5,
            plan_status="in_progress",
            running_count=1,
            completed_count=2
        )
        result = plan.to_dict()
        assert result["data"]["plan_id"] == "plan-123"
        assert result["data"]["title"] == "My Plan"
        assert result["data"]["steps"] == [{"text": "Step 1", "status": "waiting"}]
        assert result["data"]["total_steps"] == 5
        assert result["data"]["running_count"] == 1

    def test_plan_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "plan",
            "data": {
                "plan_id": "p1",
                "steps": [{"text": "Task", "status": "completed"}],
                "total_steps": 1,
                "status": "completed"
            }
        }
        plan = PlanContent.from_dict(data)
        assert plan.plan_id == "p1"
        assert len(plan.steps) == 1
        assert plan.plan_status == "completed"

    def test_convert_tasks_to_steps(self):
        """Verify task to step conversion"""
        plan = PlanContent(
            content_type=ContentType.PLAN,
            tasks=[
                {"name": "Task A", "status": "running"},
                {"name": "Task B", "status": "completed"},
                {"name": "Task C", "status": "failed", "error_message": "Error"}
            ]
        )
        steps = plan._convert_tasks_to_steps()
        assert len(steps) == 3
        assert steps[0]["text"] == "Task A"
        assert steps[0]["status"] == "running"
        assert steps[1]["status"] == "completed"
        assert steps[2]["status"] == "failed"
        assert steps[2]["error_message"] == "Error"

    def test_task_status_map(self):
        """Verify task status mapping"""
        assert _TASK_STATUS_MAP["created"] == "waiting"
        assert _TASK_STATUS_MAP["ready"] == "waiting"
        assert _TASK_STATUS_MAP["running"] == "running"
        assert _TASK_STATUS_MAP["completed"] == "completed"
        assert _TASK_STATUS_MAP["failed"] == "failed"

    def test_plan_status_map(self):
        """Verify plan status mapping"""
        assert _PLAN_STATUS_MAP["created"] == "pending"
        assert _PLAN_STATUS_MAP["running"] == "in_progress"
        assert _PLAN_STATUS_MAP["completed"] == "completed"


class TestPlanTaskContent:
    """Tests for PlanTaskContent"""

    def test_plan_task_defaults(self):
        """Verify default values"""
        task = PlanTaskContent(content_type=ContentType.PLAN_TASK)
        assert task.content_type == ContentType.PLAN_TASK
        assert task.plan_id == ""
        assert task.task_id == ""
        assert task.task_name == ""
        assert task.task_status == "waiting"

    def test_plan_task_to_dict(self):
        """Verify to_dict serialization"""
        task = PlanTaskContent(
            content_type=ContentType.PLAN_TASK,
            plan_id="plan-1",
            task_id="task-1",
            task_name="Write Scene",
            task_status="running",
            description="Writing scene 1",
            previous_status="waiting"
        )
        result = task.to_dict()
        assert result["data"]["plan_id"] == "plan-1"
        assert result["data"]["task_id"] == "task-1"
        assert result["data"]["task_name"] == "Write Scene"
        assert result["data"]["task_status"] == "running"
        assert result["data"]["previous_status"] == "waiting"

    def test_plan_task_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "plan_task",
            "data": {
                "plan_id": "p1",
                "task_id": "t1",
                "task_name": "Task",
                "task_status": "completed"
            }
        }
        task = PlanTaskContent.from_dict(data)
        assert task.plan_id == "p1"
        assert task.task_id == "t1"
        assert task.task_status == "completed"


class TestStepContent:
    """Tests for StepContent"""

    def test_step_defaults(self):
        """Verify default values"""
        step = StepContent(content_type=ContentType.STEP)
        assert step.content_type == ContentType.STEP
        assert step.step_id == ""
        assert step.step_number == 0
        assert step.step_status == "pending"

    def test_step_to_dict(self):
        """Verify to_dict serialization"""
        step = StepContent(
            content_type=ContentType.STEP,
            step_id="step-1",
            step_number=1,
            description="First step",
            step_status="completed",
            result="Success"
        )
        result = step.to_dict()
        assert result["data"]["step_id"] == "step-1"
        assert result["data"]["step_number"] == 1
        assert result["data"]["status"] == "completed"
        assert result["data"]["result"] == "Success"


class TestTaskListContent:
    """Tests for TaskListContent"""

    def test_task_list_defaults(self):
        """Verify default values"""
        tl = TaskListContent(content_type=ContentType.TASK_LIST)
        assert tl.content_type == ContentType.TASK_LIST
        assert tl.tasks == []
        assert tl.completed_count == 0
        assert tl.total_count == 0

    def test_task_list_to_dict(self):
        """Verify to_dict serialization"""
        tl = TaskListContent(
            content_type=ContentType.TASK_LIST,
            tasks=[{"name": "Task 1"}],
            completed_count=2,
            total_count=5,
            list_title="Project Tasks"
        )
        result = tl.to_dict()
        assert result["data"]["tasks"] == [{"name": "Task 1"}]
        assert result["data"]["completed_count"] == 2
        assert result["data"]["total_count"] == 5
        assert result["data"]["title"] == "Project Tasks"


class TestProgressContent:
    """Tests for ProgressContent"""

    def test_progress_defaults(self):
        """Verify default values"""
        prog = ProgressContent(content_type=ContentType.PROGRESS)
        assert prog.content_type == ContentType.PROGRESS
        assert prog.progress == ""
        assert prog.percentage is None
        assert prog.tool_name is None

    def test_progress_to_dict(self):
        """Verify to_dict serialization"""
        prog = ProgressContent(
            content_type=ContentType.PROGRESS,
            progress="Generating scene 1",
            percentage=50,
            tool_name="scene_generator"
        )
        result = prog.to_dict()
        assert result["data"]["progress"] == "Generating scene 1"
        assert result["data"]["percentage"] == 50
        assert result["data"]["tool_name"] == "scene_generator"

    def test_progress_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "progress",
            "data": {"progress": "Loading", "percentage": 75}
        }
        prog = ProgressContent.from_dict(data)
        assert prog.progress == "Loading"
        assert prog.percentage == 75

    def test_progress_is_auxiliary_content(self):
        """Verify progress is auxiliary content"""
        prog = ProgressContent(content_type=ContentType.PROGRESS)
        assert prog.is_auxiliary_content() == True


class TestSkillExecutionState:
    """Tests for SkillExecutionState enum"""

    def test_all_states(self):
        """Verify all state values"""
        assert SkillExecutionState.PENDING.value == "pending"
        assert SkillExecutionState.IN_PROGRESS.value == "in_progress"
        assert SkillExecutionState.COMPLETED.value == "completed"
        assert SkillExecutionState.ERROR.value == "error"

    def test_state_is_string_enum(self):
        """Verify SkillExecutionState is a string enum"""
        assert SkillExecutionState("pending") == SkillExecutionState.PENDING
        assert SkillExecutionState("completed") == SkillExecutionState.COMPLETED


class TestSkillContent:
    """Tests for SkillContent"""

    def test_skill_defaults(self):
        """Verify default values"""
        skill = SkillContent(content_type=ContentType.SKILL)
        assert skill.content_type == ContentType.SKILL
        assert skill.state == SkillExecutionState.PENDING
        assert skill.skill_name == ""
        assert skill.progress_percentage is None
        assert skill.result == ""
        assert skill.error_message == ""

    def test_skill_to_dict_pending(self):
        """Verify to_dict for pending state"""
        skill = SkillContent(
            content_type=ContentType.SKILL,
            state=SkillExecutionState.PENDING,
            skill_name="write_scene",
            skill_description="Write a scene"
        )
        result = skill.to_dict()
        assert result["data"]["skill_name"] == "write_scene"
        assert result["data"]["state"] == "pending"

    def test_skill_to_dict_in_progress(self):
        """Verify to_dict for in_progress state"""
        skill = SkillContent(
            content_type=ContentType.SKILL,
            state=SkillExecutionState.IN_PROGRESS,
            skill_name="generate_video",
            progress_percentage=30,
            progress_text="Rendering frames"
        )
        result = skill.to_dict()
        assert result["data"]["state"] == "in_progress"
        assert result["data"]["progress_percentage"] == 30
        assert result["data"]["progress_text"] == "Rendering frames"

    def test_skill_to_dict_completed(self):
        """Verify to_dict for completed state"""
        skill = SkillContent(
            content_type=ContentType.SKILL,
            state=SkillExecutionState.COMPLETED,
            skill_name="export",
            result="File exported successfully"
        )
        result = skill.to_dict()
        assert result["data"]["state"] == "completed"
        assert result["data"]["result"] == "File exported successfully"

    def test_skill_to_dict_error(self):
        """Verify to_dict for error state"""
        skill = SkillContent(
            content_type=ContentType.SKILL,
            state=SkillExecutionState.ERROR,
            skill_name="upload",
            error_message="Connection failed"
        )
        result = skill.to_dict()
        assert result["data"]["state"] == "error"
        assert result["data"]["error_message"] == "Connection failed"

    def test_skill_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "skill",
            "data": {
                "skill_name": "test_skill",
                "state": "in_progress",
                "progress_percentage": 50
            }
        }
        skill = SkillContent.from_dict(data)
        assert skill.skill_name == "test_skill"
        assert skill.state == SkillExecutionState.IN_PROGRESS
        assert skill.progress_percentage == 50

    def test_skill_handles_invalid_state(self):
        """Verify invalid state defaults to PENDING"""
        data = {
            "content_type": "skill",
            "data": {"skill_name": "test", "state": "invalid_state"}
        }
        skill = SkillContent.from_dict(data)
        assert skill.state == SkillExecutionState.PENDING

    def test_skill_is_auxiliary_content(self):
        """Verify skill is auxiliary content"""
        skill = SkillContent(content_type=ContentType.SKILL)
        assert skill.is_auxiliary_content() == True


class TestTextContent:
    """Tests for TextContent"""

    def test_text_defaults(self):
        """Verify default values"""
        text = TextContent(content_type=ContentType.TEXT)
        assert text.content_type == ContentType.TEXT
        assert text.text == ""

    def test_text_to_dict(self):
        """Verify to_dict serialization"""
        text = TextContent(
            content_type=ContentType.TEXT,
            text="Hello, this is a message."
        )
        result = text.to_dict()
        assert result["data"]["text"] == "Hello, this is a message."

    def test_text_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "text",
            "data": {"text": "Response text"}
        }
        text = TextContent.from_dict(data)
        assert text.text == "Response text"

    def test_text_is_main_content(self):
        """Verify text is main content"""
        text = TextContent(content_type=ContentType.TEXT)
        assert text.is_main_content() == True


class TestThinkingContent:
    """Tests for ThinkingContent"""

    def test_thinking_defaults(self):
        """Verify default values"""
        think = ThinkingContent(content_type=ContentType.THINKING)
        assert think.content_type == ContentType.THINKING
        assert think.thought == ""
        assert think.step is None
        assert think.total_steps is None

    def test_thinking_to_dict(self):
        """Verify to_dict serialization"""
        think = ThinkingContent(
            content_type=ContentType.THINKING,
            thought="Analyzing the request...",
            step=2,
            total_steps=5
        )
        result = think.to_dict()
        assert result["data"]["thought"] == "Analyzing the request..."
        assert result["data"]["step"] == 2
        assert result["data"]["total_steps"] == 5

    def test_thinking_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "thinking",
            "data": {"thought": "Planning", "step": 1, "total_steps": 3}
        }
        think = ThinkingContent.from_dict(data)
        assert think.thought == "Planning"
        assert think.step == 1
        assert think.total_steps == 3

    def test_thinking_is_auxiliary_content(self):
        """Verify thinking is auxiliary content"""
        think = ThinkingContent(content_type=ContentType.THINKING)
        assert think.is_auxiliary_content() == True