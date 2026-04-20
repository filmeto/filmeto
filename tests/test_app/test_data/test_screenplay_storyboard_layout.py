"""Screenplay directory layout and storyboard shot storage."""

from pathlib import Path

from app.data.screen_play.scene_paths import SCENE_MD_NAME, SHOTS_DIR_NAME
from app.data.screen_play.screen_play_manager import ScreenPlayManager
from app.data.story_board.story_board_manager import StoryBoardManager


def test_create_scene_uses_directory_with_scene_md_and_shots(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    mgr = ScreenPlayManager(root)
    assert mgr.create_scene("sc1", "T", "body", {})
    scene_root = root / "screen_plays" / "sc1"
    assert (scene_root / SCENE_MD_NAME).is_file()
    assert (scene_root / SHOTS_DIR_NAME).is_dir()


def test_legacy_flat_md_migrates_on_read(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    sp = root / "screen_plays"
    sp.mkdir(parents=True)
    legacy = sp / "old.md"
    legacy.write_text(
        "---\nscene_id: old\ntitle: Legacy\n---\n\nHello scene\n",
        encoding="utf-8",
    )
    mgr = ScreenPlayManager(root)
    scene = mgr.get_scene("old")
    assert scene is not None
    assert scene.content.strip() == "Hello scene"
    assert not legacy.exists()
    assert (sp / "old" / SCENE_MD_NAME).is_file()
    assert (sp / "old" / SHOTS_DIR_NAME).is_dir()


def test_storyboard_shot_roundtrip_and_key_moment(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    sm = ScreenPlayManager(root)
    assert sm.create_scene("s1", "Scene", "INT. ROOM", {})
    bm = StoryBoardManager(root)
    assert bm.create_shot(
        "s1",
        "01",
        "Opening",
        "Action line",
        {
            "visual": {"picture_content": "Wide city", "composition": " thirds"},
            "audio": {"dialogue": "None", "ambient": "rain"},
            "tech_director": {"camera_move": "Dolly in", "vfx_tags": ["lens_flare"]},
            "ux_logic": {"user_flow": "Tap continue"},
        },
    )
    shot = bm.get_shot("s1", "01")
    assert shot is not None
    assert shot.visual.picture_content == "Wide city"
    assert shot.tech_director.vfx_tags == ["lens_flare"]
    img = root / "ref.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    assert bm.set_key_moment_image("s1", "01", img)
    again = bm.get_shot("s1", "01")
    assert again is not None
    kmp = bm.key_moment_path("s1", "01")
    assert kmp is not None and kmp.is_file()


def test_delete_scene_removes_shots_tree(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    sm = ScreenPlayManager(root)
    sm.create_scene("x", "t", "c", {})
    bm = StoryBoardManager(root)
    bm.create_shot("x", "01", "", "", {})
    assert (root / "screen_plays" / "x" / "shots" / "01").is_dir()
    assert sm.delete_scene("x")
    assert not (root / "screen_plays" / "x").exists()
