import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIRS = ["agent", "app", "server", "utils"]


def _iter_source_files():
    for dirname in SOURCE_DIRS:
        base = ROOT / dirname
        for path in base.rglob("*.py"):
            yield path


def test_all_source_files_are_parseable_python():
    files = list(_iter_source_files())
    assert files, "No source files discovered under agent/app/server/utils"
    for path in files:
        content = path.read_text(encoding="utf-8")
        # Each source file is covered by this per-file AST validation.
        ast.parse(content, filename=str(path))
