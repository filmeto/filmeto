from pathlib import Path

from app.data.character import CharacterManager


class _FakeResource:
    def __init__(self, file_path: str):
        self.file_path = file_path


class _FakeResourceManager:
    def __init__(self):
        self.deleted = []

    def add_resource(self, **kwargs):
        original_name = kwargs["original_name"]
        return _FakeResource(file_path=f"resources/images/{original_name}")

    def delete_resource(self, resource_name: str):
        self.deleted.append(resource_name)
        return True


def test_create_character_and_reject_duplicates_and_empty_name(tmp_path: Path) -> None:
    mgr = CharacterManager(str(tmp_path))
    created = mgr.create_character(" Alice ", description="desc", story="story")
    duplicate = mgr.create_character("Alice")
    empty = mgr.create_character("   ")

    assert created is not None
    assert created.name == "Alice"
    assert duplicate is None
    assert empty is None
    assert (tmp_path / "characters" / "config.yml").exists()


def test_update_character_rename_and_conflict(tmp_path: Path) -> None:
    mgr = CharacterManager(str(tmp_path))
    mgr.create_character("Alice")
    mgr.create_character("Bob")

    renamed = mgr.rename_character("Alice", "Alice2")
    updated = mgr.update_character("Alice2", description="updated")
    conflict = mgr.rename_character("Alice2", "Bob")

    assert renamed is True
    assert updated is True
    assert conflict is False
    assert mgr.get_character("Alice") is None
    assert mgr.get_character("Alice2") is not None
    assert mgr.get_character("Alice2").description == "updated"


def test_add_and_remove_character_resource_via_resource_manager(tmp_path: Path) -> None:
    fake_rm = _FakeResourceManager()
    mgr = CharacterManager(str(tmp_path), resource_manager=fake_rm)
    mgr.create_character("Alice")

    source = tmp_path / "avatar.png"
    source.write_bytes(b"img")

    rel = mgr.add_resource("Alice", "main_view", str(source))
    removed = mgr.remove_resource("Alice", "main_view", remove_file=True)
    character = mgr.get_character("Alice")

    assert rel is not None
    assert character is not None
    assert "main_view" not in character.resources
    assert removed is True
    assert fake_rm.deleted == ["Alice_main_view.png"]


def test_search_and_delete_character(tmp_path: Path) -> None:
    mgr = CharacterManager(str(tmp_path))
    mgr.create_character("Hero", description="brave leader")
    mgr.create_character("Villain", story="dark past")

    search_results = [c.name for c in mgr.search_characters("dark")]
    deleted = mgr.delete_character("Villain")

    assert search_results == ["Villain"]
    assert deleted is True
    assert mgr.get_character("Villain") is None
