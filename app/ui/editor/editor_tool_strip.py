"""Editor tool category strip + per-category tool buttons (shared by MainEditor and debug UI)."""
from __future__ import annotations

from typing import Callable, Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.plugins.plugins import ToolInfo
from utils.i18n_utils import tr

TOOL_CATEGORY_ORDER = ("image", "video", "audio")
TOOL_CATEGORY_IDS: Dict[str, tuple] = {
    "image": ("text2image", "image2image", "imageedit"),
    "video": ("text2video", "image2video", "speak2video"),
    "audio": ("text2speak", "text2music"),
}
TOOL_CATEGORY_ICONS = {
    "image": "\ue6ce",
    "video": "\ue73b",
    "audio": "\ue61f",
}


def tool_category_for_tool_id(tool_id: str) -> Optional[str]:
    for cat, ids in TOOL_CATEGORY_IDS.items():
        if tool_id in ids:
            return cat
    return None


def categorized_tool_ids() -> set:
    s = set()
    for ids in TOOL_CATEGORY_IDS.values():
        s.update(ids)
    return s


class EditorToolStripWidget(QFrame):
    """Builds category_bar (image/video/audio) and tools_stack (per-category tool buttons).
    Layout host is optional: use category_bar + tools_stack as siblings in a parent layout."""

    toolButtonClicked = Signal(str)

    def __init__(self, tools: Dict[str, ToolInfo], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._tools = tools
        self.tool_buttons: Dict[str, QPushButton] = {}
        self._category_buttons: Dict[str, QPushButton] = {}
        self.category_bar: Optional[QFrame] = None
        self.tools_stack: Optional[QStackedWidget] = None
        self._category_group: Optional[QButtonGroup] = None
        self._current_tool_getter: Callable[[], Optional[str]] = lambda: None
        self._build_ui()

    def set_current_tool_getter(self, getter: Callable[[], Optional[str]]) -> None:
        self._current_tool_getter = getter

    def _build_ui(self) -> None:
        self.setObjectName("editor_tool_section")

        self.category_bar = QFrame(self)
        self.category_bar.setObjectName("editor_tool_category_bar")
        cat_layout = QVBoxLayout(self.category_bar)
        cat_layout.setContentsMargins(6, 8, 6, 8)
        cat_layout.setSpacing(6)

        self._category_group = QButtonGroup(self)
        self._category_group.setExclusive(True)

        cat_btn_size = 36
        for cat in TOOL_CATEGORY_ORDER:
            cbtn = QPushButton(TOOL_CATEGORY_ICONS[cat])
            cbtn.setObjectName("editor_tool_category_button")
            cbtn.setCheckable(True)
            cbtn.setFixedSize(cat_btn_size, cat_btn_size)
            cbtn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            cbtn.setProperty("tool_category", cat)
            if cat == "image":
                cbtn.setToolTip(tr("Image tools"))
            elif cat == "video":
                cbtn.setToolTip(tr("Video tools"))
            else:
                cbtn.setToolTip(tr("Audio tools"))
            self._category_group.addButton(cbtn)
            cat_layout.addWidget(cbtn, 0, Qt.AlignmentFlag.AlignHCenter)
            self._category_buttons[cat] = cbtn
            cbtn.clicked.connect(self._on_tool_category_clicked)
        cat_layout.addStretch()

        self.tools_stack = QStackedWidget(self)
        self.tools_stack.setObjectName("editor_tools_stack")

        page_layouts: Dict[str, QHBoxLayout] = {}
        for cat in TOOL_CATEGORY_ORDER:
            page = QWidget()
            page_layout = QHBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setSpacing(6)
            page_layouts[cat] = page_layout
            self.tools_stack.addWidget(page)

        known = categorized_tool_ids()
        for cat in TOOL_CATEGORY_ORDER:
            for tool_id in TOOL_CATEGORY_IDS[cat]:
                if tool_id not in self._tools:
                    continue
                self._make_tool_button(tool_id, page_layouts[cat])

        for tool_id in self._tools:
            if tool_id in known:
                continue
            self._make_tool_button(tool_id, page_layouts["image"])

        for cat in TOOL_CATEGORY_ORDER:
            page_layouts[cat].addStretch()

        first_cat_idx = 0
        for idx, cat in enumerate(TOOL_CATEGORY_ORDER):
            if TOOL_CATEGORY_IDS[cat] and any(
                tid in self._tools for tid in TOOL_CATEGORY_IDS[cat]
            ):
                first_cat_idx = idx
                break
        self.tools_stack.setCurrentIndex(first_cat_idx)
        if self._category_buttons:
            self._category_buttons[TOOL_CATEGORY_ORDER[first_cat_idx]].setChecked(True)

    def _make_tool_button(self, tool_id: str, page_layout: QHBoxLayout) -> None:
        tool_info = self._tools[tool_id]
        btn = QPushButton(tool_info.icon)
        btn.setObjectName("editor_tool_button")
        btn.setToolTip(tool_info.name)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setCheckable(True)
        btn.setFixedSize(40, 40)
        btn.setProperty("tool_id", tool_id)
        btn.clicked.connect(self._on_tool_button_clicked)
        self.tool_buttons[tool_id] = btn
        page_layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter)

    def _on_tool_button_clicked(self) -> None:
        button = self.sender()
        if button:
            tool_id = button.property("tool_id")
            if tool_id:
                self.toolButtonClicked.emit(tool_id)

    def _first_tool_in_category(self, cat: str) -> Optional[str]:
        for tool_id in TOOL_CATEGORY_IDS[cat]:
            if tool_id in self._tools:
                return tool_id
        if cat == "image":
            for tool_id in self._tools:
                if tool_category_for_tool_id(tool_id) is None:
                    return tool_id
        return None

    def _on_tool_category_clicked(self) -> None:
        button = self.sender()
        if not button or not self.tools_stack:
            return
        cat = button.property("tool_category")
        if not cat:
            return
        idx = TOOL_CATEGORY_ORDER.index(cat)
        self.tools_stack.setCurrentIndex(idx)
        current = self._current_tool_getter()
        if current and tool_category_for_tool_id(current) == cat:
            return
        first = self._first_tool_in_category(cat)
        if first:
            self.toolButtonClicked.emit(first)

    def sync_ui_for_tool(self, tool_id: str) -> None:
        cat = tool_category_for_tool_id(tool_id)
        if cat is None:
            cat = "image"
        if not self.tools_stack:
            return
        idx = TOOL_CATEGORY_ORDER.index(cat)
        self.tools_stack.setCurrentIndex(idx)
        for cbtn in self._category_buttons.values():
            cbtn.blockSignals(True)
        for key, cbtn in self._category_buttons.items():
            cbtn.setChecked(key == cat)
        for cbtn in self._category_buttons.values():
            cbtn.blockSignals(False)

    def apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QFrame#editor_tool_section {
                background-color: transparent;
                border: none;
            }
            """
        )
        if self.category_bar:
            self.category_bar.setStyleSheet(
                """
                QFrame#editor_tool_category_bar {
                    background-color: #25262a;
                    border: 1px solid #3d3f44;
                    border-radius: 10px;
                }
                """
            )
        tool_button_style = """
            QPushButton#editor_tool_button {
                font-family: iconfont;
                font-size: 18px;
                background-color: #3d3f4e;
                border: 2px solid #505254;
                border-radius: 6px;
                color: #888888;
            }
            QPushButton#editor_tool_button:hover {
                background-color: #4a4c5e;
                border: 2px solid #5a5c6e;
                color: #E1E1E1;
            }
            QPushButton#editor_tool_button:checked {
                background-color: #4080ff;
                border: 2px solid #4080ff;
                color: #ffffff;
            }
            QPushButton#editor_tool_button:checked:hover {
                background-color: #5090ff;
                border: 2px solid #5090ff;
            }
        """
        for btn in self.tool_buttons.values():
            btn.setStyleSheet(tool_button_style)

        r = 18
        category_btn_style = f"""
            QPushButton#editor_tool_category_button {{
                font-family: iconfont;
                font-size: 20px;
                background-color: transparent;
                border: none;
                border-radius: {r}px;
                color: #888888;
                padding: 0px;
            }}
            QPushButton#editor_tool_category_button:hover {{
                background-color: transparent;
                border: none;
                color: #E1E1E1;
            }}
            QPushButton#editor_tool_category_button:checked {{
                background-color: #4080ff;
                border: none;
                border-radius: {r}px;
                color: #ffffff;
            }}
            QPushButton#editor_tool_category_button:checked:hover {{
                background-color: #5090ff;
                border: none;
                border-radius: {r}px;
                color: #ffffff;
            }}
        """
        for cbtn in self._category_buttons.values():
            cbtn.setStyleSheet(category_btn_style)
