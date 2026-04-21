from pathlib import Path

from app.data.prompt import PromptManager, PromptTemplate
from utils.yaml_utils import load_yaml


def test_prompt_template_roundtrip() -> None:
    template = PromptTemplate(
        id="t1",
        icon="icon.png",
        text="hello",
        created_at="2026-01-01T00:00:00",
        usage_count=2,
    )
    data = template.to_dict()
    rebuilt = PromptTemplate.from_dict(data)
    assert rebuilt.id == "t1"
    assert rebuilt.text == "hello"
    assert rebuilt.usage_count == 2


def test_add_search_increment_and_delete_template(tmp_path: Path) -> None:
    manager = PromptManager(str(tmp_path / "prompts"))

    assert manager.add_template("a.png", "Write a story")
    assert not manager.add_template("b.png", "Write a story")

    templates = manager.load_templates()
    assert len(templates) == 1
    template_id = templates[0].id

    assert [t.text for t in manager.search_templates("story")] == ["Write a story"]
    assert manager.search_templates("missing") == []

    manager.increment_usage(template_id)
    reloaded = load_yaml(tmp_path / "prompts" / f"template_{template_id}.yml")
    assert reloaded["usage_count"] == 1

    assert manager.delete_template(template_id)
    assert manager.load_templates() == []


def test_load_templates_skips_invalid_files(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "template_valid.yml").write_text(
        "id: v1\nicon: i.png\ntext: ok\ncreated_at: '2026-01-01T00:00:00'\nusage_count: 3\n",
        encoding="utf-8",
    )
    (prompts_dir / "template_invalid.yml").write_text(
        "id: bad\ntext: missing required fields\n",
        encoding="utf-8",
    )

    manager = PromptManager(str(prompts_dir))
    templates = manager.load_templates()
    assert len(templates) == 1
    assert templates[0].id == "v1"
