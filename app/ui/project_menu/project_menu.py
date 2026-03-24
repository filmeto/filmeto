import logging
from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, QSize, QRectF, Signal, Slot, Qt
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QFont, QColor, QPen
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QMenu, QVBoxLayout, QLabel, QPushButton, QDialog, QLineEdit, QHBoxLayout, QDialogButtonBox

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)
PROJECT_MENU_QML_PATH = Path(__file__).resolve().parent.parent / "qml" / "project_menu" / "ProjectMenuButton.qml"


class _ProjectMenuBridge(QObject):
    projectNameChanged = Signal()
    clicked = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._project_name = ""

    @Property(str, notify=projectNameChanged)
    def projectName(self) -> str:
        return self._project_name

    def set_project_name(self, name: str) -> None:
        name = name or ""
        if self._project_name != name:
            self._project_name = name
            self.projectNameChanged.emit()

    @Slot()
    def open_menu(self) -> None:
        self.clicked.emit()


class ProjectMenu(BaseWidget):
    project_switched = Signal(str)

    def __init__(self, workspace: Workspace):
        super(ProjectMenu, self).__init__(workspace)
        self.setObjectName("project_menu")
        self.workspace = workspace

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self._bridge = _ProjectMenuBridge(self)
        self._bridge.set_project_name(workspace.project_name)
        self._bridge.clicked.connect(self._show_menu)

        self._quick = QQuickWidget(self)
        self._quick.setObjectName("project_menu_quick")
        self._quick.setFixedSize(120, 32)
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick.setAttribute(Qt.WA_TranslucentBackground, True)
        self._quick.setClearColor(Qt.transparent)
        self._quick.rootContext().setContextProperty("projectMenuBridge", self._bridge)
        self._quick.setSource(QUrl.fromLocalFile(str(PROJECT_MENU_QML_PATH)))
        self.layout.addWidget(self._quick)

        self.toolbar_menu = QMenu(self)
        self.toolbar_menu.setStyleSheet("""
            QMenu {
                background-color: #2b2d30;
                border: 1px solid #505254;
                border-radius: 5px;
                padding: 5px 0px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 5px 20px;
                font-size: 14px;
                color: #E1E1E1;
            }
            QMenu::item:selected {
                background-color: #3d3f4e;
            }
            QMenu::separator {
                height: 1px;
                background-color: #505254;
                margin: 5px 0px;
            }
        """)

        self.new_project_action = QAction(tr("新建项目"), self)
        self.toolbar_menu.addAction(self.new_project_action)
        self.toolbar_menu.addSeparator()
        self.load_existing_projects()

        self.new_project_action.triggered.connect(self.on_new_project_triggered)

    def _show_menu(self) -> None:
        anchor = self._quick.mapToGlobal(self._quick.rect().bottomLeft())
        self.toolbar_menu.exec(anchor)

    def load_existing_projects(self):
        actions = self.toolbar_menu.actions()
        for action in actions[2:]:
            self.toolbar_menu.removeAction(action)

        project_names = self.workspace.project_manager.list_projects()
        for project_name in project_names:
            if project_name != self.workspace.project_name:
                project_instance = self.workspace.project_manager.get_project(project_name)
                if not project_instance:
                    continue

                project_path = project_instance.project_path

                action = QAction(project_name, self)
                project_icon = self.create_rounded_letter_icon(
                    project_name[0].upper(),
                    size=56,
                    bg_color=QColor("blue"),
                    text_color=QColor("white"),
                    corner_radius_ratio=0.25
                )
                action.setIcon(project_icon)
                action.triggered.connect(lambda checked=False, name=project_name: self.on_project_selected(name))
                self.toolbar_menu.addAction(action)
                action.setToolTip(project_path)

    def on_project_selected(self, project_name):
        logger.info(f"选择了项目: {project_name}")

        self.workspace.switch_project(project_name)
        self._bridge.set_project_name(project_name)
        self.load_existing_projects()
        self.project_switched.emit(project_name)

    def on_new_project_triggered(self):
        from app.ui.dialog.custom_dialog import CustomDialog
        dialog = CustomDialog(self)
        dialog.set_title(tr("新建项目"))

        content_layout = QVBoxLayout()
        label = QLabel(tr("请输入项目名称:"))
        label.setStyleSheet("color: #E1E1E1; font-size: 14px;")
        content_layout.addWidget(label)

        line_edit = QLineEdit()
        line_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1e1f22;
                border: 1px solid #505254;
                border-radius: 5px;
                padding: 8px;
                color: #E1E1E1;
                selection-background-color: #4080ff;
                font-size: 14px;
            }
        """)
        content_layout.addWidget(line_edit)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal,
            dialog
        )
        button_box.setStyleSheet("""
            QPushButton {
                background-color: #3d3f4e;
                color: #E1E1E1;
                border: 1px solid #505254;
                border-radius: 5px;
                padding: 6px 15px;
                font-size: 14px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #444654;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        content_layout.addWidget(button_box)

        dialog.setContentLayout(content_layout)
        line_edit.setFocus()

        ok = dialog.exec() == QDialog.Accepted
        project_name = line_edit.text() if ok else ""

        if ok and project_name:
            try:
                self.workspace.project_manager.create_project(project_name)
                self._bridge.set_project_name(self.workspace.project_name)
                self.load_existing_projects()

                from app.ui.dialog import CustomDialog
                dialog = CustomDialog(self)
                dialog.set_title(tr("项目创建成功"))

                content_layout = QVBoxLayout()
                message_label = QLabel(tr("项目 '{}' 创建成功！").format(project_name))
                message_label.setStyleSheet("color: #E1E1E1; font-size: 14px;")
                message_label.setWordWrap(True)
                content_layout.addWidget(message_label)

                ok_button = QPushButton(tr("确定"))
                ok_button.setStyleSheet("""
                    QPushButton {
                        background-color: #3d3f4e;
                        color: #E1E1E1;
                        border: 1px solid #505254;
                        border-radius: 5px;
                        padding: 6px 15px;
                        font-size: 14px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #444654;
                    }
                    QPushButton:pressed {
                        background-color: #005a9e;
                    }
                """)
                ok_button.clicked.connect(dialog.accept)
                button_layout = QHBoxLayout()
                button_layout.addStretch()
                button_layout.addWidget(ok_button)
                button_layout.addStretch()
                content_layout.addLayout(button_layout)

                dialog.setContentLayout(content_layout)
                dialog.exec()
            except Exception as e:
                from app.ui.dialog import CustomDialog
                dialog = CustomDialog(self)
                dialog.set_title(tr("项目创建失败"))

                content_layout = QVBoxLayout()
                message_label = QLabel(tr("创建项目时出错: {}".format(str(e))))
                message_label.setStyleSheet("color: #E1E1E1; font-size: 14px;")
                message_label.setWordWrap(True)
                content_layout.addWidget(message_label)

                ok_button = QPushButton(tr("确定"))
                ok_button.setStyleSheet("""
                    QPushButton {
                        background-color: #3d3f4e;
                        color: #E1E1E1;
                        border: 1px solid #505254;
                        border-radius: 5px;
                        padding: 6px 15px;
                        font-size: 14px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #444654;
                    }
                    QPushButton:pressed {
                        background-color: #005a9e;
                    }
                """)
                ok_button.clicked.connect(dialog.accept)
                button_layout = QHBoxLayout()
                button_layout.addStretch()
                button_layout.addWidget(ok_button)
                button_layout.addStretch()
                content_layout.addLayout(button_layout)

                dialog.setContentLayout(content_layout)
                dialog.exec()

    def create_rounded_letter_icon(
        self,
        letter,
        size=32,
        bg_color=QColor("transparent"),
        text_color=QColor("black"),
        font_family="Sans-serif",
        corner_radius_ratio=0.2,
    ):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(0, 0, size, size)
        corner_radius = size * corner_radius_ratio

        from PySide6.QtGui import QPainterPath

        path = QPainterPath()
        path.addRoundedRect(rect, corner_radius, corner_radius)
        painter.setClipPath(path)

        if bg_color != Qt.transparent and bg_color.alpha() > 0:
            painter.fillRect(rect, bg_color)

        font = QFont(font_family, size // 1.5, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(text_color))
        painter.drawText(rect.toRect(), Qt.AlignCenter, letter)
        painter.end()
        return QIcon(pixmap)