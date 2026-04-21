from pathlib import Path

from app.data.screen_play.screen_play_formatter import ScreenPlayFormatter
from app.data.screen_play.screen_play_manager import ScreenPlayManager
from app.data.screen_play.screen_play_manager_factory import ScreenPlayManagerFactory
from app.data.screen_play.screen_play_scene import ScreenPlayScene


def test_screen_play_scene_to_dict_and_hollywood_format() -> None:
    scene = ScreenPlayScene(
        scene_id="s1",
        title="Opening",
        content="Body",
        location="INT. ROOM",
        characters=["Alice"],
    )
    payload = scene.to_dict()
    assert payload["scene_id"] == "s1"
    assert payload["location"] == "INT. ROOM"

    formatted = ScreenPlayScene.format_hollywood_screenplay(
        scene_heading="int. room - day",
        action="Alice enters.",
        character="alice",
        dialogue="Hello",
        parenthetical="whispering",
        transition="CUT TO:",
    )
    assert "# INT. ROOM - DAY" in formatted
    assert "**ALICE**" in formatted
    assert "_CUT TO:_" in formatted


def test_formatter_outputs_scene_sections() -> None:
    out = ScreenPlayFormatter.format_scene_content(
        scene_number="1",
        location="INT. LAB",
        time_of_day="night",
        characters=["Alice", "Bob"],
        scene_content={
            "action": "Machines hum.",
            "dialogue": [{"character": "Alice", "dialogue": "Ready?"}],
            "transition": "FADE OUT.",
        },
    )
    assert "SCENE 1: INT. LAB - NIGHT" in out
    assert "ALICE, BOB" in out
    assert "**ALICE**" in out
    assert "_FADE OUT._" in out


def test_manager_filters_bulk_and_delete_subset(tmp_path: Path) -> None:
    manager = ScreenPlayManager(tmp_path / "project")
    manager.bulk_create_scenes(
        [
            {"scene_id": "s1", "title": "A", "content": "c1", "metadata": {"characters": ["Alice"], "location": "Lab"}},
            {"scene_id": "s2", "title": "B", "content": "c2", "metadata": {"characters": ["Bob"], "location": "Street"}},
        ]
    )

    by_character = [s.scene_id for s in manager.get_scenes_by_character("Alice")]
    by_location = [s.scene_id for s in manager.get_scenes_by_location("street")]
    delete_result = manager.delete_scenes(["s1", "missing"])

    assert by_character == ["s1"]
    assert by_location == ["s2"]
    assert delete_result["deleted_scene_ids"] == ["s1"]
    assert delete_result["not_found_ids"] == ["missing"]


def test_factory_returns_cached_manager_and_remove(tmp_path: Path) -> None:
    ScreenPlayManagerFactory.clear_all()
    m1 = ScreenPlayManagerFactory.get_manager("demo", workspace_path=tmp_path)
    m2 = ScreenPlayManagerFactory.get_manager("demo", workspace_path=tmp_path)
    assert m1 is m2
    assert ScreenPlayManagerFactory.remove_manager("demo", workspace_path=tmp_path)
    assert ScreenPlayManagerFactory.get_manager("demo", workspace_path=tmp_path) is not m1
