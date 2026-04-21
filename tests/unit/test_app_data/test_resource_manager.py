from pathlib import Path

from app.data.resource import ResourceManager


def test_add_get_search_and_delete_resource(tmp_path: Path) -> None:
    manager = ResourceManager(str(tmp_path))
    source = tmp_path / "input.txt"
    source.write_text("hello", encoding="utf-8")

    resource = manager.add_resource(str(source), source_type="imported", source_id="s1")
    assert resource is not None
    assert manager.get_by_name(resource.name) is not None
    assert manager.get_by_id(resource.resource_id) is not None
    assert manager.get_by_source("imported", "s1")[0].resource_id == resource.resource_id
    assert manager.search(name_contains="input")
    assert manager.get_resource_path(resource.name) is not None

    assert manager.delete_resource(resource.name, remove_file=True)
    assert manager.get_by_name(resource.name) is None


def test_update_metadata_and_list_by_type(tmp_path: Path) -> None:
    manager = ResourceManager(str(tmp_path))
    source = tmp_path / "clip.mp3"
    source.write_bytes(b"abc")

    resource = manager.add_resource(str(source), source_type="ai_generated")
    assert resource is not None
    assert resource.media_type == "audio"
    assert manager.update_metadata(resource.name, {"k": "v"})
    updated = manager.get_by_name(resource.name)
    assert updated.metadata.get("k") == "v"
    assert manager.list_by_type("audio")


def test_validate_index_reports_missing_and_orphaned_files(tmp_path: Path) -> None:
    manager = ResourceManager(str(tmp_path))
    source = tmp_path / "img.png"
    source.write_bytes(b"fake")
    resource = manager.add_resource(str(source))
    assert resource is not None

    # Make missing indexed file
    indexed_path = tmp_path / resource.file_path
    indexed_path.unlink()

    # Create orphaned file not in index
    orphan = tmp_path / "resources" / "others" / "orphan.bin"
    orphan.write_bytes(b"x")

    report = manager.validate_index()
    assert resource.name in report["missing_files"]
    assert "resources/others/orphan.bin" in report["orphaned_files"]
