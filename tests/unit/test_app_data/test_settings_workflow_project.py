from pathlib import Path

from app.data.project import scan_valid_project_names
from app.data.settings import Settings
from app.data.workflow import WorkflowManager, WorkflowNodeMapping


def test_scan_valid_project_names_only_returns_dirs_with_project_yml(tmp_path: Path) -> None:
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    valid = projects_dir / "valid_a"
    valid.mkdir()
    (valid / "project.yml").write_text("project_name: valid_a\n", encoding="utf-8")
    invalid = projects_dir / "invalid_b"
    invalid.mkdir()
    names = scan_valid_project_names(str(projects_dir))
    assert names == ["valid_a"]


def test_settings_parse_set_validate_and_reset(tmp_path: Path) -> None:
    settings = Settings(str(tmp_path), defer_load=True)
    settings._parse_settings(
        {
            "groups": [
                {
                    "name": "general",
                    "label": "General",
                    "fields": [
                        {
                            "name": "language",
                            "type": "select",
                            "default": "en",
                            "options": [{"value": "en"}, {"value": "zh"}],
                        },
                        {
                            "name": "opacity",
                            "type": "slider",
                            "default": 60,
                            "validation": {"min": 0, "max": 100},
                        },
                    ],
                }
            ]
        }
    )
    settings._loaded = True
    settings._defer_load = False

    assert settings.get("general.language") == "en"
    assert settings.set("general.language", "zh")
    assert settings.get("general.language") == "zh"
    assert not settings.set("general.language", "jp")
    assert settings.validate("general.opacity", 80)
    assert not settings.validate("general.opacity", 120)

    settings.reset_to_defaults()
    assert settings.get("general.language") == "en"
    assert settings.is_dirty()


def test_workflow_manager_save_prepare_and_delete(tmp_path: Path) -> None:
    wm = WorkflowManager(str(tmp_path), server_name="comfyui")
    source = tmp_path / "wf.json"
    source.write_text(
        '{"1":{"inputs":{"text":"$prompt","seed":"$seed","image":"$inputImage"}}}',
        encoding="utf-8",
    )

    node_mapping = WorkflowNodeMapping(
        prompt_node="1",
        output_node="2",
        input_node="1",
        seed_node="1",
    )

    assert wm.save_workflow(
        name="My Workflow",
        workflow_type="text2image",
        workflow_file_path=str(source),
        node_mapping=node_mapping,
    )
    loaded = wm.get_workflow("My Workflow")
    assert loaded is not None
    prepared = wm.prepare_workflow("My Workflow", prompt="hello", input_image="img.png", seed=42)
    assert prepared is not None
    prepared_text = str(prepared)
    assert "hello" in prepared_text
    assert "img.png" in prepared_text
    assert "42" in prepared_text
    assert wm.delete_workflow("My Workflow")
