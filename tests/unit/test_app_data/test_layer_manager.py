from pathlib import Path

from app.data.layer import Layer, LayerManager, LayerType


class _DummyTimeline:
    def __init__(self):
        self.project = type("P", (), {"get_resolution": lambda _self: (1000, 2000)})()
        self._current_item = None

    def get_current_item(self):
        return self._current_item


class _DummyTimelineItem:
    def __init__(self, root: Path, index: int = 0):
        self.index = index
        self.layers_path = str(root / "layers")
        Path(self.layers_path).mkdir(parents=True, exist_ok=True)
        self._config = {"layers": []}
        self.timeline = _DummyTimeline()
        self.timeline._current_item = self

    def get_layers_path(self):
        return self.layers_path

    def get_config_value(self, key):
        return self._config.get(key)

    def set_config_value(self, key, value):
        self._config[key] = value

    def get_image_path(self):
        return str(Path(self.layers_path).parent / "image.png")


def test_layer_default_name_paths_and_serialization(tmp_path: Path) -> None:
    timeline_item = _DummyTimelineItem(tmp_path)
    layer = Layer(layer_id=7, layer_type=LayerType.IMAGE, timeline_item=timeline_item)
    assert layer.name == "图层-7"
    assert layer.get_layer_path().endswith("7.png")

    data = layer.to_dict()
    rebuilt = Layer.from_dict(data, timeline_item=timeline_item)
    assert rebuilt.id == 7
    assert rebuilt.type == LayerType.IMAGE

    rebuilt_unknown = Layer.from_dict({"id": 8, "type": "unknown"}, timeline_item=timeline_item)
    assert rebuilt_unknown.type == LayerType.IMAGE


def test_layer_manager_load_toggle_lock_rename_and_remove(tmp_path: Path) -> None:
    timeline_item = _DummyTimelineItem(tmp_path)
    layer_file = Path(timeline_item.layers_path) / "1.png"
    layer_file.write_bytes(b"x")
    timeline_item.set_config_value(
        "layers",
        [{"id": 1, "name": "L1", "type": "image", "visible": True, "locked": False, "x": 0, "y": 0, "width": 10, "height": 10}],
    )

    manager = LayerManager()
    manager.load_layers(timeline_item)
    assert manager.get_layer(1) is not None
    assert manager.toggle_visibility(1) is False
    assert manager.toggle_lock(1) is True
    assert manager.rename_layer(1, "Renamed")
    assert manager.get_layer(1).name == "Renamed"
    assert manager.remove_layer(1) is True
    assert manager.get_layer(1) is None


def test_get_valid_dimensions_prefers_project_resolution_without_layers(tmp_path: Path) -> None:
    timeline_item = _DummyTimelineItem(tmp_path)
    manager = LayerManager()
    manager.load_layers(timeline_item)
    assert manager.get_valid_dimensions() == (1000, 2000)
