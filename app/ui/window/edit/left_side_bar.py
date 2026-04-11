from PySide6.QtWidgets import QPushButton, QVBoxLayout
from PySide6.QtCore import Qt, Signal

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from utils.i18n_utils import tr


class MainWindowLeftSideBar(BaseWidget):
    """Left sidebar: top row switches tool panels; bottom row switches timeline mode."""

    button_clicked = Signal(str)
    timeline_mode_clicked = Signal(str)

    def __init__(self, workspace, parent):
        super(MainWindowLeftSideBar, self).__init__(workspace)
        self.setObjectName("main_window_left_bar")
        self.parent = parent
        self.setFixedWidth(40)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 10, 0, 10)
        self.layout.setSpacing(20)

        self.panel_button_map = {}
        self.timeline_mode_button_map = {}
        self.current_panel_button = None
        self.current_timeline_mode_button = None

        self.character_button = QPushButton("\ue60c", self)
        self.character_button.setFixedSize(30, 30)
        self.character_button.setCheckable(True)
        self.character_button.setToolTip(tr("Actors / characters"))
        self.character_button.clicked.connect(lambda: self._on_panel_button_clicked("actor"))
        self.layout.addWidget(self.character_button, alignment=Qt.AlignCenter)
        self.panel_button_map["actor"] = self.character_button

        self.resource_button = QPushButton("\ue6b0", self)
        self.resource_button.setFixedSize(30, 30)
        self.resource_button.setCheckable(True)
        self.resource_button.setToolTip(tr("Resources"))
        self.resource_button.clicked.connect(lambda: self._on_panel_button_clicked("resource"))
        self.layout.addWidget(self.resource_button, alignment=Qt.AlignCenter)
        self.panel_button_map["resource"] = self.resource_button

        self.model_button = QPushButton("\ue66e", self)
        self.model_button.setFixedSize(30, 30)
        self.model_button.setCheckable(True)
        self.model_button.setToolTip(tr("Models"))
        self.model_button.clicked.connect(lambda: self._on_panel_button_clicked("model"))
        self.layout.addWidget(self.model_button, alignment=Qt.AlignCenter)
        self.panel_button_map["model"] = self.model_button

        self.attach_button = QPushButton("\ue69d", self)
        self.attach_button.setFixedSize(30, 30)
        self.attach_button.setCheckable(True)
        self.attach_button.setToolTip(tr("Attachments"))
        self.attach_button.clicked.connect(lambda: self._on_panel_button_clicked("attach"))
        self.layout.addWidget(self.attach_button, alignment=Qt.AlignCenter)
        self.panel_button_map["attach"] = self.attach_button

        self.layout.addStretch(0)

        # Timeline modes (top to bottom): screenplay, storyboard, video, voice, subtitles
        self.script_mode_button = QPushButton("\ue993", self)
        self.script_mode_button.setFixedSize(30, 30)
        self.script_mode_button.setCheckable(True)
        self.script_mode_button.setToolTip(tr("Screenplay timeline"))
        self.script_mode_button.clicked.connect(
            lambda: self._on_timeline_mode_button_clicked("script")
        )
        self.layout.addWidget(self.script_mode_button, alignment=Qt.AlignCenter)
        self.timeline_mode_button_map["script"] = self.script_mode_button

        self.storyboard_mode_button = QPushButton("\ue751", self)
        self.storyboard_mode_button.setFixedSize(30, 30)
        self.storyboard_mode_button.setCheckable(True)
        self.storyboard_mode_button.setToolTip(tr("Storyboard timeline"))
        self.storyboard_mode_button.clicked.connect(
            lambda: self._on_timeline_mode_button_clicked("storyboard")
        )
        self.layout.addWidget(self.storyboard_mode_button, alignment=Qt.AlignCenter)
        self.timeline_mode_button_map["storyboard"] = self.storyboard_mode_button

        self.video_mode_button = QPushButton("\ue6de", self)
        self.video_mode_button.setFixedSize(30, 30)
        self.video_mode_button.setCheckable(True)
        self.video_mode_button.setToolTip(tr("Video timeline"))
        self.video_mode_button.clicked.connect(
            lambda: self._on_timeline_mode_button_clicked("video")
        )
        self.layout.addWidget(self.video_mode_button, alignment=Qt.AlignCenter)
        self.timeline_mode_button_map["video"] = self.video_mode_button

        self.voice_mode_button = QPushButton("\ue709", self)
        self.voice_mode_button.setFixedSize(30, 30)
        self.voice_mode_button.setCheckable(True)
        self.voice_mode_button.setToolTip(tr("Voice / dubbing timeline"))
        self.voice_mode_button.clicked.connect(
            lambda: self._on_timeline_mode_button_clicked("voice")
        )
        self.layout.addWidget(self.voice_mode_button, alignment=Qt.AlignCenter)
        self.timeline_mode_button_map["voice"] = self.voice_mode_button

        self.subtitle_mode_button = QPushButton("\ue6b7", self)
        self.subtitle_mode_button.setFixedSize(30, 30)
        self.subtitle_mode_button.setCheckable(True)
        self.subtitle_mode_button.setToolTip(tr("Subtitle timeline"))
        self.subtitle_mode_button.clicked.connect(
            lambda: self._on_timeline_mode_button_clicked("subtitle")
        )
        self.layout.addWidget(self.subtitle_mode_button, alignment=Qt.AlignCenter)
        self.timeline_mode_button_map["subtitle"] = self.subtitle_mode_button

        self._set_selected_panel_internal("actor")
        self._set_selected_timeline_mode_internal("video")

    def _on_panel_button_clicked(self, panel_name: str):
        self._set_selected_panel_internal(panel_name)
        self.button_clicked.emit(panel_name)

    def _on_timeline_mode_button_clicked(self, mode: str):
        self._set_selected_timeline_mode_internal(mode)
        self.timeline_mode_clicked.emit(mode)

    def _set_selected_panel_internal(self, panel_name: str):
        if self.current_panel_button:
            self.current_panel_button.setChecked(False)
        if panel_name in self.panel_button_map:
            btn = self.panel_button_map[panel_name]
            btn.setChecked(True)
            self.current_panel_button = btn

    def _set_selected_timeline_mode_internal(self, mode: str):
        if self.current_timeline_mode_button:
            self.current_timeline_mode_button.setChecked(False)
        if mode in self.timeline_mode_button_map:
            btn = self.timeline_mode_button_map[mode]
            btn.setChecked(True)
            self.current_timeline_mode_button = btn

    def set_selected_button(self, panel_name: str):
        """Sync left tool panel highlight from workspace (top group only)."""
        if panel_name in self.panel_button_map:
            self._set_selected_panel_internal(panel_name)

