from pathlib import Path

from app.data.timeline import Timeline, TimelineItem


class _DummyProject:
    def __init__(self):
        self.config = {"timeline_index": 0, "timeline_size": 0}
        self._item_durations = {}
        self._timeline_duration = 0.0

    async def ensure_project_config_loaded_async(self):
        return None

    def get_timeline_index(self):
        return self.config.get("timeline_index", 0)

    def update_config(self, key, value):
        self.config[key] = value

    def set_item_duration(self, idx, duration):
        self._item_durations[str(idx)] = duration

    def has_item_duration(self, idx):
        return str(idx) in self._item_durations

    def get_item_duration(self, idx):
        return self._item_durations.get(str(idx), 1.0)

    def calculate_timeline_duration(self):
        return float(sum(self._item_durations.values()))

    def set_timeline_duration(self, value):
        self._timeline_duration = value


def _make_timeline_root(tmp_path: Path, count: int) -> Path:
    root = tmp_path / "timeline"
    root.mkdir(parents=True, exist_ok=True)
    for i in range(1, count + 1):
        d = root / str(i)
        d.mkdir(parents=True, exist_ok=True)
        (d / "layers").mkdir(exist_ok=True)
        (d / "tasks").mkdir(exist_ok=True)
    return root


def test_timeline_item_prompt_set_get_with_tool_scope(tmp_path: Path) -> None:
    root = _make_timeline_root(tmp_path, 1)
    project = _DummyProject()
    timeline = Timeline(workspace=None, project=project, timelinePath=str(root))
    item = TimelineItem(timeline, str(root), 1)

    item.set_prompt("global prompt")
    item.set_prompt("tool prompt", tool_name="text2image")

    assert item.get_prompt() == "global prompt"
    assert item.get_prompt("text2image") == "tool prompt"


def test_timeline_get_items_and_list_items_only_include_existing_content(tmp_path: Path) -> None:
    root = _make_timeline_root(tmp_path, 2)
    project = _DummyProject()
    project.update_config("timeline_index", 1)
    timeline = Timeline(workspace=None, project=project, timelinePath=str(root))

    (root / "1" / "image.png").write_bytes(b"x")
    items = timeline.get_items()
    listed = timeline.list_items()

    assert len(items) == 1
    assert items[0].index == 1
    assert listed["total_items"] == 2
    assert listed["current_index"] == 1


def test_timeline_delete_and_move_item_update_index(tmp_path: Path) -> None:
    root = _make_timeline_root(tmp_path, 3)
    project = _DummyProject()
    project.update_config("timeline_index", 2)
    project.update_config("timeline_size", 3)
    timeline = Timeline(workspace=None, project=project, timelinePath=str(root))

    assert timeline.delete_item(2)
    assert timeline.get_item_count() == 2
    assert project.get_timeline_index() == 1
    assert (root / "2").exists()  # former index 3 shifted to 2

    # now move item 2 -> 1
    assert timeline.move_item(2, 1)
    assert project.get_timeline_index() == 2  # moved around selected item tracking rule
