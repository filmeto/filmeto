# -*- coding: utf-8 -*-
"""
Project Startup Widget

This is the main container widget for a single project's startup view.
It focuses on a single project with both chat and crew member functionality.
"""
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel
)
from PySide6.QtCore import Signal, Qt, QTimer

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)

# Right tool-panel column width in startup work area (chat gets the remainder).
_STARTUP_RIGHT_PANEL_TARGET_PX = 380


class ProjectStartupWidget(BaseWidget):
    """
    Main container widget for a single project's startup view.

    Structure:
    - Left side: Crew member list
    - Right side: Chat functionality
    """

    enter_edit_mode = Signal(str)  # Emits project name when entering edit mode

    def __init__(
        self,
        window,
        workspace: Workspace,
        project_name: str = None,
        parent=None,
        defer_components: bool = False,
    ):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        self.window = window
        self.project_name = project_name
        self.setObjectName("project_startup_widget")
        self._defer_components = defer_components
        self._work_area_attached = not defer_components

        self._setup_ui()
        if not defer_components:
            self._connect_signals()
            self._apply_styles()
            if self.project_name:
                self.set_project(self.project_name)
        else:
            self._apply_styles()

    def _setup_ui(self):
        """Set up the UI components."""
        from PySide6.QtWidgets import QSplitter

        self._member_double_clicked_connected = False

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(0)

        self.work_area_splitter = QSplitter(Qt.Horizontal)
        self.work_area_splitter.setCollapsible(0, False)
        self.work_area_splitter.setCollapsible(1, False)

        if self._defer_components:
            self.agent_chat_component = None
            self.right_panel_switcher = None
            self.right_sidebar = None

            self.chat_tab = QWidget()
            self.chat_tab.setObjectName("startup_chat_skeleton")
            chat_lay = QVBoxLayout(self.chat_tab)
            chat_lay.setContentsMargins(0, 0, 0, 0)
            chat_hint = QLabel(tr("Loading"))
            chat_hint.setAlignment(Qt.AlignCenter)
            chat_hint.setStyleSheet("color: #808080; font-size: 14px;")
            chat_lay.addStretch()
            chat_lay.addWidget(chat_hint)
            chat_lay.addStretch()
            self.work_area_splitter.addWidget(self.chat_tab)

            self._panel_shell = QWidget()
            self._panel_shell.setObjectName("startup_panel_skeleton")
            self._panel_shell.setMinimumWidth(300)
            self._panel_shell.setMaximumWidth(600)
            ps_lay = QVBoxLayout(self._panel_shell)
            ps_lay.setContentsMargins(8, 8, 8, 8)
            ps_lay.addStretch()
            panel_hint = QLabel(tr("Loading"))
            panel_hint.setAlignment(Qt.AlignCenter)
            panel_hint.setStyleSheet("color: #808080; font-size: 14px;")
            ps_lay.addWidget(panel_hint)
            ps_lay.addStretch()
            self.work_area_splitter.addWidget(self._panel_shell)
        else:
            self.chat_tab = QWidget()
            self._setup_chat_tab(self.chat_tab)
            self.work_area_splitter.addWidget(self.chat_tab)

            from app.ui.window.startup.panel_switcher import StartupWindowWorkspaceTopRightBar

            self.right_panel_switcher = StartupWindowWorkspaceTopRightBar(self.workspace, self)
            self.work_area_splitter.addWidget(self.right_panel_switcher)

            self.right_panel_switcher.setMinimumWidth(300)
            self.right_panel_switcher.setMaximumWidth(600)

        self.work_area_splitter.setStretchFactor(0, 1)
        self.work_area_splitter.setStretchFactor(1, 0)

        self.main_splitter.addWidget(self.work_area_splitter)

        if self._defer_components:
            self._sidebar_shell = QWidget()
            self._sidebar_shell.setObjectName("startup_sidebar_skeleton")
            self._sidebar_shell.setFixedWidth(40)
            self.main_splitter.addWidget(self._sidebar_shell)
        else:
            from app.ui.window.startup.right_side_bar import StartupWindowRightSideBar

            self.right_sidebar = StartupWindowRightSideBar(self.workspace, self)
            self.right_sidebar.setFixedWidth(40)
            self.main_splitter.addWidget(self.right_sidebar)

        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)

        main_layout.addWidget(self.main_splitter)

        if not self._defer_components:
            self.right_sidebar.button_clicked.connect(self.right_panel_switcher.switch_to_panel)
            QTimer.singleShot(50, lambda: self._preheat_panel("members"))

        QTimer.singleShot(0, self._apply_work_area_split_sizes)

    def _apply_work_area_split_sizes(self):
        """Keep chat vs right panel ratio stable; replaceWidget resets QSplitter sizes (~50/50)."""
        sp = self.work_area_splitter
        if sp.count() < 2:
            return
        total = sp.width()
        if total <= 0:
            QTimer.singleShot(0, self._apply_work_area_split_sizes)
            return
        handle = sp.handleWidth()
        panel_w = min(
            600,
            max(300, min(_STARTUP_RIGHT_PANEL_TARGET_PX, int(total * 0.28))),
        )
        chat_w = max(200, total - panel_w - handle)
        sp.setSizes([chat_w, panel_w])

    def _preheat_panel(self, panel_name: str) -> None:
        """Load default right tool panel after the first frame (keeps initial paint light)."""
        rs = getattr(self, "right_sidebar", None)
        if rs is None:
            return
        rs.set_selected_button(panel_name, emit_signal=True)

    def attach_work_area_components(self):
        """Replace skeleton widgets with chat, panel switcher, and sidebar (main-thread)."""
        if self._work_area_attached:
            return
        self._work_area_attached = True

        new_chat_tab = QWidget()
        self._setup_chat_tab(new_chat_tab)
        self.work_area_splitter.replaceWidget(0, new_chat_tab)
        self.chat_tab.deleteLater()
        self.chat_tab = new_chat_tab

        from app.ui.window.startup.panel_switcher import StartupWindowWorkspaceTopRightBar

        self.right_panel_switcher = StartupWindowWorkspaceTopRightBar(self.workspace, self)
        self.right_panel_switcher.setMinimumWidth(300)
        self.right_panel_switcher.setMaximumWidth(600)
        self.work_area_splitter.replaceWidget(1, self.right_panel_switcher)
        self._panel_shell.deleteLater()

        from app.ui.window.startup.right_side_bar import StartupWindowRightSideBar

        self.right_sidebar = StartupWindowRightSideBar(self.workspace, self)
        self.right_sidebar.setFixedWidth(40)
        self.main_splitter.replaceWidget(1, self.right_sidebar)
        self._sidebar_shell.deleteLater()

        self.right_sidebar.button_clicked.connect(self.right_panel_switcher.switch_to_panel)
        self._connect_signals()
        QTimer.singleShot(50, lambda: self._preheat_panel("members"))

        if self.project_name:
            self.set_project(self.project_name)

        QTimer.singleShot(0, self._apply_work_area_split_sizes)
        QTimer.singleShot(50, self._apply_work_area_split_sizes)

    def _setup_chat_tab(self, tab: QWidget):
        """Set up the chat tab."""
        # Import the agent chat component
        from app.ui.chat.agent_chat import AgentChatWidget

        # Create the agent chat component
        self.agent_chat_component = AgentChatWidget(
            self.workspace, tab, defer_chat_list=True
        )

        # Set up the layout for the chat tab
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.agent_chat_component)

    def _connect_signals(self):
        """Connect signals between components."""
        if hasattr(self, 'agent_chat_component') and self.agent_chat_component:
            self.agent_chat_component.crew_member_activity.connect(self._on_crew_member_activity)

        if hasattr(self, 'right_panel_switcher'):
            self.right_panel_switcher.panel_switched.connect(self._on_panel_switched)

    def _on_crew_member_activity(self, member_name: str, is_active: bool):
        """Handle crew member activity updates.

        Args:
            member_name: Name of the crew member
            is_active: True if the member is active (thinking/typing), False otherwise
        """
        # Get the members panel from the right panel switcher
        if hasattr(self, 'right_panel_switcher'):
            members_panel = self.right_panel_switcher.get_panel('members')
            if members_panel and hasattr(members_panel, 'agent_chat_members_component'):
                members_panel.agent_chat_members_component.set_member_active(member_name, is_active)

    def _on_panel_switched(self, panel_name: str):
        """Connect member double-click signal when members panel first loads."""
        if panel_name == 'members':
            members_panel = self.right_panel_switcher.get_panel('members')
            if members_panel and hasattr(members_panel, 'agent_chat_members_component'):
                comp = members_panel.agent_chat_members_component
                # Only disconnect if we previously connected
                if self._member_double_clicked_connected:
                    try:
                        comp.member_double_clicked.disconnect(self._on_member_double_clicked)
                    except RuntimeError:
                        pass  # Signal may have been disconnected elsewhere
                    self._member_double_clicked_connected = False

                # Connect the signal
                comp.member_double_clicked.connect(self._on_member_double_clicked)
                self._member_double_clicked_connected = True

    def _on_member_double_clicked(self, crew_member):
        """Handle double-click on a crew member to open private chat."""
        if hasattr(self, 'agent_chat_component') and self.agent_chat_component:
            self.agent_chat_component.open_private_chat(crew_member)

    def _apply_styles(self):
        """Apply styles to the widget."""
        # Styles are now in the global stylesheet
        pass

    def _on_edit_project(self, project_name: str = None):
        """Handle edit project request."""
        # Use the provided project name or the one set during initialization
        project_to_edit = project_name or self.project_name

        # Switch to the project and enter edit mode
        if project_to_edit:
            self.workspace.switch_project(project_to_edit)
            self.enter_edit_mode.emit(project_to_edit)
        else:
            # If no project name is provided, emit the signal anyway
            # This allows the caller to determine the project to edit
            self.enter_edit_mode.emit(self.workspace.project_name)

    def _on_prompt_submitted(self, prompt: str):
        """Handle prompt submission."""
        # Make sure the agent chat component is initialized
        if hasattr(self, 'agent_chat_component') and self.agent_chat_component:
            # Send the message to the agent chat component
            self.agent_chat_component._on_message_submitted(prompt)


    def refresh_project(self):
        """Refresh the current project info."""
        pass  # No-op since we removed project info functionality

    def set_project(self, project_name: str):
        """Set the project to display."""
        previous_project = self.project_name
        self.project_name = project_name
        if not self._work_area_attached:
            return

        # Update the agent chat component with the new project context
        # Only clear chat history if actually switching to a different project
        if hasattr(self, 'agent_chat_component') and self.agent_chat_component:
            # Update the agent's project context
            project = self.workspace.get_project()
            if not project and project_name:
                # If project is not loaded but name is provided, try to load it
                try:
                    project = self.workspace.project_manager.get_project(project_name)
                    if project:
                        self.workspace.set_current_project(project_name)
                except Exception as e:
                    logger.error(f"Error loading project {project_name}: {e}")

            if project:
                self.agent_chat_component.on_project_switch(project)

            # Only clear chat history if this is a different project
            # For the same project, we want to preserve the loaded history
            if previous_project and previous_project != project_name:
                logger.info(f"Switched from project '{previous_project}' to '{project_name}', clearing history")
                _chw = getattr(self.agent_chat_component, "chat_history_widget", None)
                if _chw is not None:
                    _chw.clear()
            elif previous_project == project_name:
                logger.debug(f"Same project '{project_name}', preserving history")

        # Update the agent chat members component with the new project context
        if hasattr(self, 'agent_chat_members_component') and self.agent_chat_members_component:
            # Load crew members for the project
            self._load_crew_members()

    def _load_crew_members(self):
        """Load and display crew members for the current project."""
        # Get the current project
        project = self.workspace.get_project()
        if not project:
            return

        # Get the crew members for the project
        try:
            from agent.crew import CrewService

            # Initialize crew service
            crew_service = CrewService()

            # Get all crew members for the project
            crew_members = crew_service.list_crew_members(project)

            # Set the members in the members panel
            if hasattr(self, 'members_panel') and self.members_panel:
                self.members_panel.set_members(crew_members)
        except Exception as e:
            logger.error(f"Error loading crew members: {e}")
