from pathlib import Path

import app.data.project as project_module
from app.data.project import ProjectManager


class _DummyProject:
    def __init__(self, _workspace, project_path, project_name, load_data=True):
        self.project_path = project_path
        self.project_name = project_name
        self.load_data = load_data
        self.updated = {}

    def update_config(self, key, value):
        self.updated[key] = value


def test_create_project_builds_structure_and_registers_project(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(project_module, "Project", _DummyProject)
    manager = ProjectManager(str(tmp_path), defer_scan=True)

    created = manager.create_project("demo")

    assert created is not None
    assert manager.get_project("demo") is created
    assert (tmp_path / "projects" / "demo" / "project.yml").exists()
    assert (tmp_path / "projects" / "demo" / "timeline").is_dir()
    assert (tmp_path / "projects" / "demo" / "resources" / "images").is_dir()
    assert (tmp_path / "projects" / "demo" / "agent" / "chats").is_dir()


def test_update_switch_and_delete_project(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(project_module, "Project", _DummyProject)
    manager = ProjectManager(str(tmp_path), defer_scan=True)
    manager.create_project("p1")

    assert manager.update_project("p1", {"k": 1, "name": "v"})
    project = manager.get_project("p1")
    assert project.updated == {"k": 1, "name": "v"}

    switched = manager.switch_project("p1")
    assert switched is project

    assert manager.delete_project("p1")
    assert manager.get_project("p1") is None
    assert not (tmp_path / "projects" / "p1").exists()


def test_replace_and_list_projects_from_names(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(project_module, "Project", _DummyProject)
    manager = ProjectManager(str(tmp_path), defer_scan=True)

    project_root = tmp_path / "projects"
    (project_root / "a").mkdir(parents=True)
    (project_root / "b").mkdir(parents=True)
    (project_root / "a" / "project.yml").write_text("project_name: a\n", encoding="utf-8")
    (project_root / "b" / "project.yml").write_text("project_name: b\n", encoding="utf-8")

    manager.replace_projects_from_names(["b", "a"])
    listed = sorted(manager.list_projects())

    assert listed == ["a", "b"]
