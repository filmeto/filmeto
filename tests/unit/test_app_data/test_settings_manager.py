from pathlib import Path

from app.data.settings import Settings
from utils.yaml_utils import load_yaml


def _build_settings(tmp_path: Path) -> Settings:
    settings = Settings(str(tmp_path), defer_load=True)
    settings._parse_settings(
        {
            "groups": [
                {
                    "name": "general",
                    "label": "General",
                    "icon": "icon-general",
                    "fields": [
                        {
                            "name": "username",
                            "type": "text",
                            "default": "user",
                            "validation": {"min_length": 2, "max_length": 10, "pattern": r"^[a-zA-Z0-9_]+$"},
                        },
                        {
                            "name": "volume",
                            "type": "number",
                            "default": 10,
                            "validation": {"min": 0, "max": 100},
                        },
                        {
                            "name": "enabled",
                            "type": "boolean",
                            "default": True,
                        },
                        {
                            "name": "theme",
                            "type": "select",
                            "default": "dark",
                            "options": [{"value": "dark"}, {"value": "light"}],
                        },
                        {
                            "name": "accent",
                            "type": "color",
                            "default": "#112233",
                            "validation": {"format": "hex"},
                        },
                    ],
                }
            ]
        }
    )
    settings._loaded = True
    settings._defer_load = False
    return settings


def test_settings_validate_all_supported_types(tmp_path: Path) -> None:
    s = _build_settings(tmp_path)
    assert s.validate("general.username", "abc_1")
    assert not s.validate("general.username", "a")
    assert not s.validate("general.username", "bad-value")
    assert s.validate("general.volume", 50)
    assert not s.validate("general.volume", 200)
    assert s.validate("general.enabled", False)
    assert not s.validate("general.enabled", "true")
    assert s.validate("general.theme", "light")
    assert not s.validate("general.theme", "blue")
    assert s.validate("general.accent", "#A1B2C3")
    assert not s.validate("general.accent", "red")


def test_settings_set_get_group_and_dirty_flags(tmp_path: Path) -> None:
    s = _build_settings(tmp_path)
    assert s.get("general.username") == "user"
    assert s.set("general.username", "new_user")
    assert s.get("general.username") == "new_user"
    assert s.is_dirty()
    assert not s.set("general.missing", 1)
    assert s.get("bad-format", "fallback") == "fallback"
    group = s.get_group("general")
    assert group is not None
    assert group.icon == "icon-general"


def test_settings_save_writes_expected_payload_and_clears_dirty(tmp_path: Path) -> None:
    s = _build_settings(tmp_path)
    s.set("general.theme", "light")
    assert s.save()
    raw = load_yaml(tmp_path / "settings.yml")
    fields = {f["name"]: f for f in raw["groups"][0]["fields"]}
    assert fields["theme"]["value"] == "light"
    assert not s.is_dirty()
