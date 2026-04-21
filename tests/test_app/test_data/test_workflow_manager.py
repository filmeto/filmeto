from pathlib import Path

from app.data.workflow import WorkflowManager, WorkflowMetadata, WorkflowNodeMapping


def test_workflow_models_roundtrip() -> None:
    mapping = WorkflowNodeMapping(prompt_node="1", output_node="2", input_node="3", seed_node="4")
    meta = WorkflowMetadata(
        name="WF",
        type="text2image",
        file="wf.json",
        node_mapping=mapping,
        description="d",
        author="u",
        tags=["a"],
    )
    rebuilt = WorkflowMetadata.from_dict(meta.to_dict())
    assert rebuilt.name == "WF"
    assert rebuilt.node_mapping.prompt_node == "1"
    assert rebuilt.tags == ["a"]


def test_workflow_manager_import_export_and_lookup(tmp_path: Path) -> None:
    wm = WorkflowManager(str(tmp_path), server_name="comfyui")
    src = tmp_path / "external.json"
    src.write_text('{"1":{"inputs":{"text":"$prompt"}}}', encoding="utf-8")

    assert wm.import_workflow(str(src), name="External One")
    assert (tmp_path / "servers" / "comfyui" / "workflows" / "external_one_workflow.json").exists()

    # no metadata yet for imported-only workflow
    assert wm.get_workflow("External One") is None

    mapping = WorkflowNodeMapping(prompt_node="1", output_node="1")
    assert wm.save_workflow(
        name="External One",
        workflow_type="text2image",
        workflow_file_path=str(src),
        node_mapping=mapping,
    )
    wf = wm.get_workflow("External One")
    assert wf is not None
    assert wm.get_workflow_by_type("text2image") is not None

    export_target = tmp_path / "exported.json"
    assert wm.export_workflow("External One", str(export_target))
    assert export_target.exists()


def test_workflow_manager_load_and_prepare_content(tmp_path: Path) -> None:
    wm = WorkflowManager(str(tmp_path), server_name="comfyui")
    src = tmp_path / "wf.json"
    src.write_text('{"1":{"inputs":{"text":"$prompt","seed":"$seed","img":"$inputImage"}}}', encoding="utf-8")
    mapping = WorkflowNodeMapping(prompt_node="1", output_node="1", input_node="1", seed_node="1")
    assert wm.save_workflow("WF", "image_edit", str(src), mapping)

    metadata = wm.load_workflow_metadata("WF")
    content = wm.load_workflow_content("WF")
    prepared = wm.prepare_workflow("WF", prompt="hello", input_image="a.png", seed=7)

    assert metadata is not None
    assert content is not None
    assert prepared is not None
    prepared_text = str(prepared)
    assert "hello" in prepared_text
    assert "a.png" in prepared_text
    assert "7" in prepared_text
