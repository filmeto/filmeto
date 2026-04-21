from app.data.screen_play.scene_paths import SCENE_MD_NAME, SHOT_MD_NAME, SHOTS_DIR_NAME
from app.data.screen_play.screen_play_formatter import ScreenPlayFormatter
from app.data.screen_play.screen_play_manager_factory import ScreenPlayManagerFactory


def test_scene_path_constants_match_storage_contract():
    assert SCENE_MD_NAME == "scene.md"
    assert SHOTS_DIR_NAME == "shots"
    assert SHOT_MD_NAME == "shot.md"


def test_formatter_handles_optional_sections_and_parenthetical_shape():
    content = ScreenPlayFormatter.format_scene_content(
        scene_number="7",
        location="EXT. BEACH",
        time_of_day="dawn",
        characters=[],
        scene_content={
            "scene_heading": "ext. beach - dawn",
            "dialogue": [{"character": "narrator", "parenthetical": "v.o.", "dialogue": "The sea wakes."}],
        },
    )

    assert "SCENE 7: EXT. BEACH - DAWN" in content
    assert "# EXT. BEACH - DAWN" in content
    assert "**NARRATOR**" in content
    assert "*(v.o.)*" in content
    assert "CHARACTERS PRESENT" not in content


def test_factory_list_cached_managers_and_get_manager_by_path(tmp_path):
    ScreenPlayManagerFactory.clear_all()
    manager = ScreenPlayManagerFactory.get_manager("p1", workspace_path=tmp_path)
    cached = ScreenPlayManagerFactory.list_cached_managers()
    assert len(cached) == 1
    key = (str(tmp_path), "p1")
    assert key in cached
    assert cached[key].endswith("/projects/p1")

    by_path = ScreenPlayManagerFactory.get_manager_by_path(tmp_path / "projects" / "direct")
    assert by_path is not manager
    assert str(by_path.project_path).endswith("/projects/direct")
