from pathlib import Path

from utils.markdown_parser import has_markdown_code_blocks, parse_markdown_blocks
from utils.path_utils import ensure_project_dirs, get_project_path, get_workspace_path
from utils.progress_utils import Progress


def test_get_workspace_path_prefers_env(monkeypatch, tmp_path):
    monkeypatch.setenv("FILMETO_WORKSPACE", str(tmp_path / "env_ws"))
    assert get_workspace_path() == tmp_path / "env_ws"


def test_get_workspace_path_uses_cwd_workspace(monkeypatch, tmp_path):
    monkeypatch.delenv("FILMETO_WORKSPACE", raising=False)
    ws = tmp_path / "workspace"
    ws.mkdir()
    monkeypatch.chdir(tmp_path)
    assert get_workspace_path() == ws


def test_get_project_path_and_ensure_dirs(tmp_path):
    project_path = get_project_path("demo", workspace_path=tmp_path)
    assert project_path == tmp_path / "projects" / "demo"

    ensure_project_dirs(project_path)
    for d in ("screen_plays", "scripts", "assets", "exports"):
        assert (project_path / d).exists()


def test_parse_markdown_blocks_mixed_content():
    text = "Intro\n```python\nprint('x')\n```\nOutro"
    segments = parse_markdown_blocks(text)
    assert segments[0]["type"] == "text"
    assert segments[1]["type"] == "code_block"
    assert segments[1]["language"] == "python"
    assert "print('x')" in segments[1]["code"]
    assert segments[2]["type"] == "text"


def test_parse_markdown_blocks_unclosed_fence_stays_text():
    text = "Hi\n```js\nconsole.log(1)"
    segments = parse_markdown_blocks(text)
    assert len(segments) == 2
    assert segments[0]["type"] == "text"
    assert segments[1]["type"] == "text"
    assert "```js" in segments[1]["text"]


def test_has_markdown_code_blocks_requires_open_and_close():
    assert has_markdown_code_blocks("a\n```py\nx\n```")
    assert not has_markdown_code_blocks("a\n```py\nx")
    assert not has_markdown_code_blocks("plain text")


def test_progress_updates_percent_and_logs():
    p = Progress()
    p.set_total(5)
    p.on_log("start")
    p.set_current(2)
    assert p.get_total() == 5
    assert p.get_current() == 2
    assert p.percent == 40
    assert p.logs == "start"
