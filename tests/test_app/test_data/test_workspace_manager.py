from pathlib import Path

import app.data.workspace as workspace_module
from app.data.workspace import Workspace


class _DummyProject:
    def __init__(self, workspace, project_path, project_name, load_data=False):
        self.workspace = workspace
        self.project_path = project_path
        self.project_name = project_name
        self.load_data = load_data
        self.calls = []

    def connect_task_create(self, f):
        self.calls.append(("connect_task_create", f))

    def connect_task_execute(self, f):
        self.calls.append(("connect_task_execute", f))

    def connect_task_progress(self, f):
        self.calls.append(("connect_task_progress", f))

    def connect_task_finished(self, f):
        self.calls.append(("connect_task_finished", f))

    def connect_timeline_switch(self, f):
        self.calls.append(("connect_timeline_switch", f))

    def connect_layer_changed(self, f):
        self.calls.append(("connect_layer_changed", f))

    def connect_timeline_position(self, f):
        self.calls.append(("connect_timeline_position", f))

    def submit_task(self, params, timeline_item_id=None):
        self.calls.append(("submit_task", params, timeline_item_id))

    def on_task_finished(self, result):
        self.calls.append(("on_task_finished", result))

    def get_timeline(self):
        return type("T", (), {"get_current_item": lambda _self: "cur"})()


class _DummyProjectManager:
    def __init__(self, workspace_root_path, defer_scan=False):
        self.workspace_root_path = workspace_root_path
        self.defer_scan = defer_scan
        self.projects = {}
        self.switched = []
        self.project_switched = type("S", (), {"connect": lambda _self, _f: None})()

    def create_project(self, project_name):
        ppath = str(Path(self.workspace_root_path) / "projects" / project_name)
        proj = _DummyProject(None, ppath, project_name, load_data=False)
        self.projects[project_name] = proj
        return proj

    def get_project(self, project_name):
        return self.projects.get(project_name)

    def switch_project(self, project_name):
        self.switched.append(project_name)
        return self.projects.get(project_name)


class _DummyPromptManager:
    def __init__(self, prompts_dir):
        self.prompts_dir = prompts_dir


class _DummySettings:
    def __init__(self, workspace_path, defer_load=False):
        self.workspace_path = workspace_path
        self.defer_load = defer_load


class _DummyPlugins:
    def __init__(self, workspace, defer_discovery=False):
        self.workspace = workspace
        self.defer_discovery = defer_discovery


def _patch_workspace_dependencies(monkeypatch):
    monkeypatch.setattr(workspace_module, "Project", _DummyProject)
    monkeypatch.setattr(workspace_module, "ProjectManager", _DummyProjectManager)
    monkeypatch.setattr(workspace_module, "PromptManager", _DummyPromptManager)
    monkeypatch.setattr(workspace_module, "Settings", _DummySettings)
    monkeypatch.setattr("app.plugins.plugins.Plugins", _DummyPlugins)


def test_workspace_deferred_bootstrap_and_project_property(tmp_path: Path, monkeypatch) -> None:
    _patch_workspace_dependencies(monkeypatch)
    ws_root = tmp_path / "ws"
    ws_root.mkdir(parents=True)
    (ws_root / "projects" / "demo").mkdir(parents=True)

    ws = Workspace(str(ws_root), "demo", defer_heavy_init=True)
    assert ws._project is None  # deferred
    project = ws.project  # lazy bootstrap
    assert project is not None
    assert project.project_name == "demo"
    assert "demo" in ws.project_manager.projects


def test_workspace_switch_project_updates_paths_and_managers(tmp_path: Path, monkeypatch) -> None:
    _patch_workspace_dependencies(monkeypatch)
    ws_root = tmp_path / "ws"
    ws_root.mkdir(parents=True)

    ws = Workspace(str(ws_root), "a", defer_heavy_init=False)
    switched = ws.switch_project("b")

    assert switched.project_name == "b"
    assert ws.project_name == "b"
    assert ws.project_path.endswith("/projects/b")
    assert ws.prompt_manager.prompts_dir.endswith("/projects/b/prompts")
    assert ws.project_manager.switched[-1] == "b"


def test_workspace_delegate_methods_forward_to_project(tmp_path: Path, monkeypatch) -> None:
    _patch_workspace_dependencies(monkeypatch)
    ws_root = tmp_path / "ws"
    ws_root.mkdir(parents=True)
    ws = Workspace(str(ws_root), "p", defer_heavy_init=False)

    ws.submit_task({"x": 1}, timeline_item_id=3)
    ws.on_task_finished("done")

    assert ("submit_task", {"x": 1}, 3) in ws.project.calls
    assert ("on_task_finished", "done") in ws.project.calls
    assert ws.get_current_timeline_item() == "cur"
