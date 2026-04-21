import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PLAN_PATH = ROOT / "test_plan.md"
ENTRY_RE = re.compile(r"- \[x\] `([^`]+\.py)` ✅")


def _iter_plan_python_files():
    assert PLAN_PATH.exists(), "test_plan.md not found"
    content = PLAN_PATH.read_text(encoding="utf-8")
    paths = ENTRY_RE.findall(content)
    assert paths, "No python file entries found in test_plan.md"
    for rel in paths:
        yield ROOT / rel


def test_plan_driven_files_are_parseable_python():
    for path in _iter_plan_python_files():
        assert path.exists(), f"Missing source file referenced by test plan: {path}"
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))
