from types import SimpleNamespace

from app.data.drawing import Drawing


class _DummyProject:
    def __init__(self, drawing=None):
        self._config = {}
        if drawing is not None:
            self._config["drawing"] = drawing
        self.updated = []

    def get_config(self):
        return self._config

    def update_config(self, key, value):
        self.updated.append((key, value))


def test_drawing_uses_default_when_project_has_no_drawing():
    project = _DummyProject()
    drawing = Drawing(SimpleNamespace(), project)
    assert drawing.current_tool == "pen"
    assert drawing.get_tool_setting("pen", "size") == "2"
    assert drawing.get_tool_setting("brush", "opacity") == "100"


def test_update_tool_setting_and_get_default_value():
    project = _DummyProject({"current_tool": "brush", "tool_settings": {}})
    drawing = Drawing(SimpleNamespace(), project)
    drawing.update_tool_setting("brush", "size", "10")
    assert drawing.get_tool_setting("brush", "size") == "10"
    assert drawing.get_tool_setting("brush", "missing", "fallback") == "fallback"


def test_update_persists_to_project_config():
    project = _DummyProject()
    drawing = Drawing(SimpleNamespace(), project)
    new_drawing = Drawing(SimpleNamespace(), _DummyProject())
    new_drawing.current_tool = "eraser"
    new_drawing.tool_settings = {"eraser": {"size": "33"}}

    drawing.update(new_drawing)

    assert drawing.current_tool == "eraser"
    assert drawing.tool_settings["eraser"]["size"] == "33"
    assert project.updated[-1][0] == "drawing"
    assert project.updated[-1][1]["current_tool"] == "eraser"
