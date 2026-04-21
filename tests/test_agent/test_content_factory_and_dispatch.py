from agent.chat.agent_chat_types import ContentType
from agent.chat.content import (
    PlanContent,
    PlanTaskContent,
    StructureContent,
    TextContent,
    create_content,
)


def test_create_content_returns_specific_subclass() -> None:
    content = create_content(ContentType.TEXT, text="hello")
    assert isinstance(content, TextContent)
    assert content.text == "hello"


def test_create_content_falls_back_for_unknown_mapping(monkeypatch) -> None:
    monkeypatch.setattr("agent.chat.content._CONTENT_CLASS_MAP", {})
    content = create_content(ContentType.TEXT, title="fallback")
    assert isinstance(content, StructureContent)
    assert content.title == "fallback"


def test_structure_content_from_dict_dispatches_to_plan_task() -> None:
    payload = {
        "content_id": "cid-1",
        "content_type": "plan_task",
        "status": "creating",
        "data": {
            "plan_id": "p1",
            "task_id": "t1",
            "task_name": "Draft",
            "task_status": "running",
        },
    }
    content = StructureContent.from_dict(payload)
    assert isinstance(content, PlanTaskContent)
    assert content.task_id == "t1"
    assert content.task_status == "running"


def test_plan_content_to_dict_converts_tasks_to_qml_steps() -> None:
    content = PlanContent(
        plan_id="p1",
        tasks=[
            {"id": "t1", "name": "Task A", "status": "created"},
            {"id": "t2", "name": "Task B", "status": "running"},
            {"id": "t3", "name": "Task C", "status": "completed"},
        ],
    )
    data = content.to_dict()["data"]
    steps = data["steps"]
    assert [step["status"] for step in steps] == ["waiting", "running", "completed"]
