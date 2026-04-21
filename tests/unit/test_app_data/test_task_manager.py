from pathlib import Path

from app.data.task import Task, TaskProgress, TaskResult
from utils.yaml_utils import save_yaml


class _DummyProgressManager:
    def __init__(self):
        self.progress_events = []

    def on_task_progress(self, progress):
        self.progress_events.append((progress.percent, progress.logs))


class _DummyResult:
    def get_image_path(self):
        return "/tmp/a.png"

    def get_video_path(self):
        return "/tmp/a.mp4"


class _DummyResultWithAudio(_DummyResult):
    def get_audio_path(self):
        return "/tmp/a.mp3"


def test_task_update_from_config_and_shot_flags(tmp_path: Path) -> None:
    task_dir = tmp_path / "0"
    task_dir.mkdir()
    options = {"tool": "text2image", "is_shot_task": True, "shot_id": "01", "scene_id": "s1"}
    task = Task(task_storage_manager=object(), progress_callback_manager=_DummyProgressManager(), path=str(task_dir), options=options)
    save_yaml(task_dir / "config.yml", {"task_type": "image2video", "progress": 40, "status": "done", "log": "ok"})

    task.update_from_config()

    assert task.tool == "image2video"
    assert task.percent == 40
    assert task.status == "done"
    assert task.log == "ok"
    assert task.is_shot_task() is True
    assert task.get_shot_id() == "01"
    assert task.get_scene_id() == "s1"


def test_task_result_audio_fallback_and_accessors(tmp_path: Path) -> None:
    task_dir = tmp_path / "1"
    task_dir.mkdir()
    task = Task(task_storage_manager=object(), progress_callback_manager=_DummyProgressManager(), path=str(task_dir), options={"timeline_index": 3})

    no_audio = TaskResult(task, _DummyResult())
    with_audio = TaskResult(task, _DummyResultWithAudio())

    assert no_audio.get_audio_path() is None
    assert with_audio.get_audio_path() == "/tmp/a.mp3"
    assert no_audio.get_timeline_index() == 3
    assert no_audio.get_timeline_item_id() == 3
    assert no_audio.get_task_id() == "1"


def test_task_progress_persists_and_notifies(tmp_path: Path) -> None:
    task_dir = tmp_path / "2"
    task_dir.mkdir()
    manager = _DummyProgressManager()
    task = Task(task_storage_manager=object(), progress_callback_manager=manager, path=str(task_dir), options={})
    progress = TaskProgress(task)

    progress.on_progress(55, "running")

    assert task.options["percent"] == 55
    assert task.options["logs"] == "running"
    assert manager.progress_events == [(55, "running")]
