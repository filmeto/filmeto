"""
测试新增的StructureContent类和使用示例。

本文件展示了所有新增的StructureContent类的使用方法。
"""
import pytest
from agent.chat.content import (
    AudioContent,
    TableContent,
    ChartContent,
    LinkContent,
    ButtonContent,
    FormContent,
    SkillContent,
    PlanContent,
    StepContent,
    TaskListContent,
    ThinkingContent,
    create_content,
)
from agent.chat.agent_chat_types import ContentType
from agent.event.agent_event import AgentEvent, AgentEventType


class TestAudioContent:
    """测试音频内容。"""

    def test_create_audio_content(self):
        """测试创建音频内容。"""
        audio = AudioContent(
            url="http://example.com/audio.mp3",
            thumbnail_url="http://example.com/thumb.jpg",
            duration=120,
            transcript="This is a transcript",
            title="Audio File",
            description="Audio description"
        )

        assert audio.content_type == ContentType.AUDIO
        assert audio.url == "http://example.com/audio.mp3"
        assert audio.duration == 120
        assert audio.transcript == "This is a transcript"

    def test_audio_to_dict(self):
        """测试音频内容转换为字典。"""
        audio = AudioContent(
            url="http://example.com/audio.mp3",
            duration=120
        )
        data = audio.to_dict()

        assert data["content_type"] == "audio"
        assert data["data"]["url"] == "http://example.com/audio.mp3"
        assert data["data"]["duration"] == 120


class TestTableContent:
    """测试表格内容。"""

    def test_create_table_content(self):
        """测试创建表格内容。"""
        table = TableContent(
            headers=["Name", "Age", "City"],
            rows=[
                ["Alice", "25", "New York"],
                ["Bob", "30", "San Francisco"],
                ["Charlie", "35", "Boston"]
            ],
            table_title="User Information",
            description="User data table"
        )

        assert table.content_type == ContentType.TABLE
        assert len(table.headers) == 3
        assert len(table.rows) == 3
        assert table.table_title == "User Information"

    def test_table_to_dict(self):
        """测试表格内容转换为字典。"""
        table = TableContent(
            headers=["Name", "Age"],
            rows=[["Alice", "25"]]
        )
        data = table.to_dict()

        assert data["content_type"] == "table"
        assert data["data"]["headers"] == ["Name", "Age"]
        assert data["data"]["rows"] == [["Alice", "25"]]


class TestChartContent:
    """测试图表内容。"""

    def test_create_chart_content(self):
        """测试创建图表内容。"""
        chart = ChartContent(
            chart_type="bar",
            data={
                "labels": ["Jan", "Feb", "Mar"],
                "datasets": [{
                    "label": "Sales",
                    "data": [10, 20, 30]
                }]
            },
            chart_title="Monthly Sales",
            x_axis_label="Month",
            y_axis_label="Sales ($)"
        )

        assert chart.content_type == ContentType.CHART
        assert chart.chart_type == "bar"
        assert "labels" in chart.data

    def test_chart_to_dict(self):
        """测试图表内容转换为字典。"""
        chart = ChartContent(
            chart_type="line",
            data={"x": [1, 2, 3], "y": [4, 5, 6]}
        )
        data = chart.to_dict()

        assert data["content_type"] == "chart"
        assert data["data"]["chart_type"] == "line"
        assert "data" in data["data"]


class TestLinkContent:
    """测试链接内容。"""

    def test_create_link_content(self):
        """测试创建链接内容。"""
        link = LinkContent(
            url="https://example.com",
            link_title="Example Site",
            description="An example website",
            favicon_url="https://example.com/favicon.ico"
        )

        assert link.content_type == ContentType.LINK
        assert link.url == "https://example.com"
        assert link.link_title == "Example Site"

    def test_link_to_dict(self):
        """测试链接内容转换为字典。"""
        link = LinkContent(url="https://example.com")
        data = link.to_dict()

        assert data["content_type"] == "link"
        assert data["data"]["url"] == "https://example.com"


class TestButtonContent:
    """测试按钮内容。"""

    def test_create_button_content(self):
        """测试创建按钮内容。"""
        button = ButtonContent(
            label="Submit",
            action="submit_form",
            button_style="primary",
            disabled=False,
            payload={"form_id": "form123"}
        )

        assert button.content_type == ContentType.BUTTON
        assert button.label == "Submit"
        assert button.action == "submit_form"
        assert button.button_style == "primary"

    def test_button_to_dict(self):
        """测试按钮内容转换为字典。"""
        button = ButtonContent(
            label="Click Me",
            action="click"
        )
        data = button.to_dict()

        assert data["content_type"] == "button"
        assert data["data"]["label"] == "Click Me"
        assert data["data"]["action"] == "click"


class TestFormContent:
    """测试表单内容。"""

    def test_create_form_content(self):
        """测试创建表单内容。"""
        form = FormContent(
            fields=[
                {"name": "email", "type": "email", "label": "Email", "required": True},
                {"name": "message", "type": "textarea", "label": "Message"}
            ],
            submit_action="send_message",
            submit_label="Send",
            form_title="Contact Form"
        )

        assert form.content_type == ContentType.FORM
        assert len(form.fields) == 2
        assert form.submit_action == "send_message"

    def test_form_to_dict(self):
        """测试表单内容转换为字典。"""
        form = FormContent(
            fields=[{"name": "name", "type": "text"}],
            submit_action="save"
        )
        data = form.to_dict()

        assert data["content_type"] == "form"
        assert len(data["data"]["fields"]) == 1
        assert data["data"]["submit_action"] == "save"


class TestSkillContent:
    """测试技能信息内容。"""

    def test_create_skill_content(self):
        """测试创建技能内容。"""
        skill = SkillContent(
            skill_name="writer",
            skill_description="Write creative content",
            parameters=[
                {"name": "topic", "type": "string", "required": True},
                {"name": "style", "type": "string", "required": False}
            ],
            example_call='writer(topic="AI", style="technical")',
            usage_criteria="Use when you need to generate written content"
        )

        assert skill.content_type == ContentType.SKILL
        assert skill.skill_name == "writer"
        assert len(skill.parameters) == 2

    def test_skill_to_dict(self):
        """测试技能内容转换为字典。"""
        skill = SkillContent(
            skill_name="analyzer",
            skill_description="Analyze data"
        )
        data = skill.to_dict()

        assert data["content_type"] == "skill"
        assert data["data"]["skill_name"] == "analyzer"


class TestPlanContent:
    """测试计划内容。"""

    def test_create_plan_content(self):
        """测试创建计划内容。"""
        plan = PlanContent(
            plan_id="plan_123",
            plan_title="Content Creation Plan",
            steps=[
                {"step_id": "step1", "description": "Research topic", "status": "pending"},
                {"step_id": "step2", "description": "Write draft", "status": "pending"},
                {"step_id": "step3", "description": "Review and edit", "status": "pending"}
            ],
            current_step=0,
            total_steps=3,
            plan_status="pending"
        )

        assert plan.content_type == ContentType.PLAN
        assert plan.plan_id == "plan_123"
        assert len(plan.steps) == 3
        assert plan.plan_status == "pending"

    def test_plan_to_dict(self):
        """测试计划内容转换为字典。"""
        plan = PlanContent(
            plan_id="plan_456",
            steps=[{"step": "task1"}],
            total_steps=1
        )
        data = plan.to_dict()

        assert data["content_type"] == "plan"
        assert data["data"]["plan_id"] == "plan_456"
        assert data["data"]["total_steps"] == 1


class TestStepContent:
    """测试步骤内容。"""

    def test_create_step_content(self):
        """测试创建步骤内容。"""
        step = StepContent(
            step_id="step_1",
            step_number=1,
            description="Write the first draft",
            step_status="in_progress",
            result="Draft completed",
            estimated_duration=300
        )

        assert step.content_type == ContentType.STEP
        assert step.step_number == 1
        assert step.step_status == "in_progress"
        assert step.estimated_duration == 300

    def test_step_complete(self):
        """测试步骤完成状态。"""
        step = StepContent(
            step_id="step_1",
            step_number=1,
            description="Test step"
        )
        step.complete()

        assert step.status.value == "completed"

    def test_step_fail(self):
        """测试步骤失败状态。"""
        step = StepContent(
            step_id="step_1",
            step_number=1,
            description="Test step"
        )
        step.fail("Execution failed")

        assert step.status.value == "failed"
        # fail方法将error存储在metadata中
        assert step.metadata.get("error") == "Execution failed"


class TestTaskListContent:
    """测试任务列表内容。"""

    def test_create_task_list_content(self):
        """测试创建任务列表内容。"""
        task_list = TaskListContent(
            tasks=[
                {"id": "task1", "description": "Write documentation", "completed": False},
                {"id": "task2", "description": "Run tests", "completed": True},
                {"id": "task3", "description": "Deploy", "completed": False}
            ],
            completed_count=1,
            total_count=3,
            list_title="Project Tasks"
        )

        assert task_list.content_type == ContentType.TASK_LIST
        assert len(task_list.tasks) == 3
        assert task_list.completed_count == 1
        assert task_list.total_count == 3

    def test_task_list_to_dict(self):
        """测试任务列表转换为字典。"""
        task_list = TaskListContent(
            tasks=[{"id": "task1", "description": "Task 1"}],
            total_count=1,
            completed_count=0
        )
        data = task_list.to_dict()

        assert data["content_type"] == "task_list"
        assert data["data"]["total_count"] == 1
        assert len(data["data"]["tasks"]) == 1


class TestCreateContentFactory:
    """测试内容工厂函数。"""

    def test_create_audio(self):
        """测试创建音频内容。"""
        content = create_content(
            ContentType.AUDIO,
            url="http://example.com/audio.mp3",
            duration=120
        )
        assert isinstance(content, AudioContent)
        assert content.content_type == ContentType.AUDIO

    def test_create_table(self):
        """测试创建表格内容。"""
        content = create_content(
            ContentType.TABLE,
            headers=["A", "B"],
            rows=[["1", "2"]]
        )
        assert isinstance(content, TableContent)
        assert content.content_type == ContentType.TABLE

    def test_create_chart(self):
        """测试创建图表内容。"""
        content = create_content(
            ContentType.CHART,
            chart_type="bar",
            data={}
        )
        assert isinstance(content, ChartContent)
        assert content.content_type == ContentType.CHART

    def test_create_link(self):
        """测试创建链接内容。"""
        content = create_content(
            ContentType.LINK,
            url="https://example.com"
        )
        assert isinstance(content, LinkContent)
        assert content.content_type == ContentType.LINK

    def test_create_button(self):
        """测试创建按钮内容。"""
        content = create_content(
            ContentType.BUTTON,
            label="Click",
            action="submit"
        )
        assert isinstance(content, ButtonContent)
        assert content.content_type == ContentType.BUTTON

    def test_create_form(self):
        """测试创建表单内容。"""
        content = create_content(
            ContentType.FORM,
            fields=[],
            submit_action="save"
        )
        assert isinstance(content, FormContent)
        assert content.content_type == ContentType.FORM

    def test_create_skill(self):
        """测试创建技能内容。"""
        content = create_content(
            ContentType.SKILL,
            skill_name="test",
            skill_description="Test skill"
        )
        assert isinstance(content, SkillContent)
        assert content.content_type == ContentType.SKILL

    def test_create_plan(self):
        """测试创建计划内容。"""
        content = create_content(
            ContentType.PLAN,
            plan_id="plan123",
            steps=[]
        )
        assert isinstance(content, PlanContent)
        assert content.content_type == ContentType.PLAN

    def test_create_step(self):
        """测试创建步骤内容。"""
        content = create_content(
            ContentType.STEP,
            step_id="step1",
            step_number=1,
            description="Test step"
        )
        assert isinstance(content, StepContent)
        assert content.content_type == ContentType.STEP

    def test_create_task_list(self):
        """测试创建任务列表内容。"""
        content = create_content(
            ContentType.TASK_LIST,
            tasks=[],
            total_count=0,
            completed_count=0
        )
        assert isinstance(content, TaskListContent)
        assert content.content_type == ContentType.TASK_LIST


class TestAgentEventWithNewContent:
    """测试使用新内容类型的AgentEvent。"""

    def test_plan_event(self):
        """测试计划事件。"""
        plan = PlanContent(
            plan_id="plan123",
            steps=[],
            total_steps=3
        )

        event = AgentEvent.create(
            event_type=AgentEventType.PLAN_CREATED.value,
            project_name="test_project",
            react_type="crew",
            run_id="run123",
            step_id=1,
            sender_id="planner",
            sender_name="Planner",
            content=plan
        )

        assert event.event_type == AgentEventType.PLAN_CREATED.value
        assert isinstance(event.content, PlanContent)
        assert event.content.plan_id == "plan123"

    def test_skill_event(self):
        """测试技能事件。"""
        skill = SkillContent(
            skill_name="writer",
            skill_description="Write content"
        )

        event = AgentEvent.create(
            event_type=AgentEventType.SKILL_START.value,
            project_name="test_project",
            react_type="crew",
            run_id="run123",
            step_id=1,
            content=skill
        )

        assert event.event_type == AgentEventType.SKILL_START.value
        assert isinstance(event.content, SkillContent)

    def test_crew_member_event(self):
        """测试Crew成员事件。"""
        thinking = ThinkingContent(
            thought="Analyzing the task...",
            step=1,
            total_steps=5
        )

        event = AgentEvent.create(
            event_type=AgentEventType.CREW_MEMBER_THINKING.value,
            project_name="test_project",
            react_type="crew",
            run_id="run123",
            step_id=1,
            sender_id="writer",
            sender_name="Writer",
            content=thinking
        )

        assert event.event_type == AgentEventType.CREW_MEMBER_THINKING.value
        assert isinstance(event.content, ThinkingContent)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
