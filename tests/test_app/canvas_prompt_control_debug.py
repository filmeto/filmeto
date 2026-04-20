#!/usr/bin/env python3
"""Debug window: CanvasPromptWidget + EditorToolStripWidget (rounded shell, icon-only category toggles)."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_iconfont() -> None:
    from PySide6.QtGui import QFontDatabase

    ttf = _REPO_ROOT / "textures" / "iconfont.ttf"
    if ttf.exists():
        QFontDatabase.addApplicationFont(str(ttf))


def main() -> int:
    from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget

    from app.data.workspace import Workspace
    from app.ui.editor.editor_tool_strip import EditorToolStripWidget
    from app.ui.prompt.canvas_prompt_widget import CanvasPromptWidget
    from utils.i18n_utils import tr

    _load_iconfont()
    app = QApplication(sys.argv)

    ws = Workspace(
        str(_REPO_ROOT / "workspace"),
        "debug_canvas_prompt",
        defer_heavy_init=True,
    )
    ws.plugins.ensure_discovery()
    tools = ws.plugins.get_tool_registry()

    win = QMainWindow()
    win.setWindowTitle("Canvas prompt + tool strip debug")
    win.resize(920, 280)

    holder = QWidget()
    outer = QVBoxLayout(holder)
    outer.setContentsMargins(16, 16, 16, 16)

    hint = QLabel(
        "Debug: outer shell is rounded; category icons sit in a rounded bar; "
        "unchecked = glyph only, checked = circular fill. Submit prints to stdout."
    )
    hint.setStyleSheet("color: #aaa; font-size: 12px;")
    outer.addWidget(hint)

    shell = QFrame()
    shell.setObjectName("debug_control_shell")
    shell.setMinimumHeight(188)
    row = QHBoxLayout(shell)
    row.setContentsMargins(12, 12, 12, 12)
    row.setSpacing(14)

    strip = EditorToolStripWidget(tools, shell)
    strip.apply_styles()

    state: dict[str, str | None] = {"tool": None}

    prompt_wrap = QFrame()
    prompt_wrap.setObjectName("debug_prompt_wrap")
    pw_layout = QVBoxLayout(prompt_wrap)
    pw_layout.setContentsMargins(0, 0, 0, 0)

    prompt = CanvasPromptWidget(ws)

    def get_tool_name():
        t = state["tool"]
        return t if isinstance(t, str) else None

    prompt.get_current_tool_name = get_tool_name  # type: ignore[method-assign]

    def select_tool(tool_id: str) -> None:
        state["tool"] = tool_id
        info = tools.get(tool_id)
        if info:
            prompt.set_placeholder(
                tr("Enter prompt for {tool}...").replace("{tool}", info.name)
            )
        for btn in strip.tool_buttons.values():
            btn.setChecked(btn.property("tool_id") == tool_id)
        strip.sync_ui_for_tool(tool_id)

    strip.toolButtonClicked.connect(select_tool)

    def on_submit(text: str) -> None:
        print(f"[debug submit] tool={state['tool']!r} prompt={text!r}", flush=True)

    prompt.prompt_submitted.connect(on_submit)

    pw_layout.addWidget(prompt)
    row.addWidget(strip, 0)
    row.addWidget(prompt_wrap, 1)

    shell.setStyleSheet(
        """
        QFrame#debug_control_shell {
            background-color: #1e1f22;
            border: 1px solid #505254;
            border-radius: 14px;
        }
        QFrame#debug_prompt_wrap {
            background-color: transparent;
            border: none;
        }
        """
    )

    outer.addWidget(shell)
    win.setCentralWidget(holder)

    if tools:
        select_tool(next(iter(tools.keys())))

    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
