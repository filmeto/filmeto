from pathlib import Path

from app.data.screen_play.screen_play_manager import ScreenPlayManager
from app.data.story_board.story_board_manager import StoryBoardManager
from app.data.story_board.story_board_shot import StoryBoardShot


def test_story_board_shot_from_metadata_and_to_metadata() -> None:
    shot = StoryBoardShot.from_metadata(
        scene_id="s1",
        shot_id="01",
        metadata={"shot_no": "1.01", "keyframe_context": {"visual": {"picture_content": "Wide"}}},
        content="Action line",
    )
    payload = shot.to_metadata()
    assert shot.description == "Action line"
    assert payload["shot_no"] == "1.01"
    assert payload["keyframe_context"]["visual"]["picture_content"] == "Wide"


def test_story_board_manager_create_update_delete_and_list(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    sm = ScreenPlayManager(project)
    assert sm.create_scene("s1", "Scene", "Body", {"scene_number": "1"})

    bm = StoryBoardManager(project)
    assert bm.create_shot("s1", "01", "T", "Initial desc", {"keyframe_context": {"audio": {"ambient": "wind"}}})

    shot = bm.get_shot("s1", "01")
    assert shot is not None
    assert shot.shot_no == "1.01"
    assert shot.keyframe_context["audio"]["ambient"] == "wind"

    assert bm.update_shot("s1", "01", {"description": "Updated", "keyframe_context": {"visual": {"picture_content": "Close"}}})
    updated = bm.get_shot("s1", "01")
    assert updated is not None
    assert updated.description == "Updated"
    assert updated.keyframe_context["visual"]["picture_content"] == "Close"

    assert bm.list_shot_ids("s1") == ["01"]
    assert len(bm.list_shots("s1")) == 1
    assert bm.delete_shot("s1", "01")
    assert bm.get_shot("s1", "01") is None


def test_story_board_key_moment_image_set_and_clear(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    sm = ScreenPlayManager(project)
    assert sm.create_scene("s1", "Scene", "Body", {})
    bm = StoryBoardManager(project)
    assert bm.create_shot("s1", "01", "", "", {})

    image = tmp_path / "source.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)

    assert bm.set_key_moment_image("s1", "01", image)
    kmp = bm.key_moment_path("s1", "01")
    assert kmp is not None and kmp.is_file()
    shot = bm.get_shot("s1", "01")
    assert shot is not None and shot.key_moment_relpath.startswith("key_moment")

    assert bm.clear_key_moment_image("s1", "01")
    assert bm.key_moment_path("s1", "01") is None
