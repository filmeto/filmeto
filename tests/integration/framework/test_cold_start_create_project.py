import os
import subprocess
import sys
from pathlib import Path


def test_cold_start_and_create_project(tmp_path: Path) -> None:
    project_name = "it_cold_start_demo"
    script = r"""
import os
import sys
import types
from pathlib import Path

# Keep startup integration deterministic by stubbing plugin discovery.
plugins_mod = types.ModuleType("app.plugins.plugins")
class _Plugins:
    def __init__(self, workspace, defer_discovery=False):
        self.workspace = workspace
        self.defer_discovery = defer_discovery
plugins_mod.Plugins = _Plugins
sys.modules["app.plugins.plugins"] = plugins_mod

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
from app.data.workspace import Workspace

main_path = Path(sys.argv[1])
project_name = sys.argv[2]

workspace_root = main_path / "workspace"
workspace_root.mkdir(parents=True, exist_ok=True)

_app = QApplication([])
ws = Workspace(str(workspace_root), project_name, load_data=False, defer_heavy_init=True)
proj = ws.project  # lazy bootstrap create/load

project_dir = workspace_root / "projects" / project_name
project_yml = project_dir / "project.yml"

if not project_dir.exists():
    raise SystemExit("project_dir_not_created")
if not project_yml.exists():
    raise SystemExit("project_yml_not_created")
if proj.project_name != project_name:
    raise SystemExit("project_name_mismatch")
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path), project_name],
        check=False,
        env={**os.environ, "PYTHONPATH": str(Path.cwd())},
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, (
        f"cold start integration failed: rc={completed.returncode}, "
        f"stdout={completed.stdout}, stderr={completed.stderr}"
    )
