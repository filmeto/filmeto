from types import SimpleNamespace

from agent.plan.plan_models import PlanInstance, PlanStatus, PlanTask, TaskStatus
from agent.plan.plan_service import PlanService


def _build_service(tmp_path):
    workspace = SimpleNamespace(workspace_path=str(tmp_path))
    service = PlanService(workspace=workspace, project_name="demo")
    return service


def test_validate_and_clean_tasks_filters_reserved_invalid_and_circular(tmp_path) -> None:
    service = _build_service(tmp_path)

    valid = PlanTask(
        id="t1",
        name="valid",
        description="ok",
        title="writer",
        needs=[],
    )
    reserved_role = PlanTask(
        id="t2",
        name="reserved",
        description="bad",
        title="assistant",
        needs=[],
    )
    missing_dep = PlanTask(
        id="t3",
        name="missing-dep",
        description="bad",
        title="reviewer",
        needs=["not-exist"],
    )
    cycle_a = PlanTask(
        id="t4",
        name="cycle-a",
        description="bad",
        title="editor",
        needs=["t5"],
    )
    cycle_b = PlanTask(
        id="t5",
        name="cycle-b",
        description="bad",
        title="editor",
        needs=["t4"],
    )

    cleaned = service._validate_and_clean_tasks(
        [valid, reserved_role, missing_dep, cycle_a, cycle_b]
    )

    assert [task.id for task in cleaned] == ["t1"]


def test_start_and_complete_plan_transitions(tmp_path) -> None:
    service = _build_service(tmp_path)

    first = PlanTask(id="a", name="A", description="A", title="writer", needs=[])
    second = PlanTask(id="b", name="B", description="B", title="writer", needs=["a"])
    plan_instance = PlanInstance(
        plan_id="p1",
        instance_id="pi1",
        project_name="demo",
        tasks=[first, second],
    )

    assert service.start_plan_execution(plan_instance)
    assert plan_instance.status == PlanStatus.RUNNING
    assert first.status == TaskStatus.READY
    assert second.status == TaskStatus.CREATED

    assert service.mark_task_running(plan_instance, "a")
    assert first.status == TaskStatus.RUNNING

    assert service.mark_task_completed(plan_instance, "a")
    assert first.status == TaskStatus.COMPLETED
    assert second.status == TaskStatus.READY

    assert service.mark_task_running(plan_instance, "b")
    assert service.mark_task_completed(plan_instance, "b")
    assert second.status == TaskStatus.COMPLETED
    assert plan_instance.status == PlanStatus.COMPLETED


def test_mark_task_failed_updates_plan_status(tmp_path) -> None:
    service = _build_service(tmp_path)
    task = PlanTask(id="f1", name="F", description="F", title="writer")
    plan_instance = PlanInstance(
        plan_id="p1",
        instance_id="pi2",
        project_name="demo",
        tasks=[task],
    )

    assert service.start_plan_execution(plan_instance)
    assert service.mark_task_failed(plan_instance, "f1", "boom")
    assert task.status == TaskStatus.FAILED
    assert task.error_message == "boom"
    assert plan_instance.status == PlanStatus.FAILED
