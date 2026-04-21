from types import SimpleNamespace

import pytest

from app.data.story_board.shot_task_manager import ShotTaskManager


@pytest.mark.asyncio
async def test_create_task_injects_shot_context_and_persists_config(tmp_path):
    shot = SimpleNamespace(scene_id="scene_1", shot_id="shot_2")
    executor = SimpleNamespace()
    manager = ShotTaskManager(shot=shot, shot_dir=str(tmp_path), executor=executor)
    options = {"tool": "text2image", "prompt": "a sunset"}

    task = await manager.create_task(options)

    assert task is not None
    assert task.is_shot_task() is True
    assert task.get_scene_id() == "scene_1"
    assert task.get_shot_id() == "shot_2"
    assert options["is_shot_task"] is True
    assert (tmp_path / "keyframes" / "0" / "config.yml").exists()


@pytest.mark.asyncio
async def test_load_all_tasks_async_loads_numeric_dirs_only(tmp_path):
    shot = SimpleNamespace(scene_id="scene_1", shot_id="shot_2")
    executor = SimpleNamespace()
    manager = ShotTaskManager(shot=shot, shot_dir=str(tmp_path), executor=executor)

    await manager.create_task({"tool": "text2image", "prompt": "one"})
    await manager.create_task({"tool": "text2image", "prompt": "two"})
    (tmp_path / "keyframes" / "misc").mkdir(parents=True, exist_ok=True)

    manager.tasks.clear()
    loaded = await manager.load_all_tasks_async(apply=True)

    assert len(loaded) == 2
    assert set(manager.tasks.keys()) == {"0", "1"}
    assert manager.get_task_by_id("0") is not None
    assert len(manager.get_all_tasks()) == 2
