# -*- coding: utf-8 -*-
"""
Project Startup Widget

This is the main container widget for a single project's startup view.
It focuses on a single project with both chat and crew member functionality.
"""
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedLayout
)
from PySide6.QtCore import Signal, Qt, QUrl
from PySide6.QtGui import QColor
from PySide6.QtQuickWidgets import QQuickWidget

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)
PROJECT_STARTUP_HOST_QML_PATH = Path(__file__).resolve().parent.parent.parent / "qml" / "startup" / "ProjectStartupHost.qml"


class ProjectStartupWidget(BaseWidget):
    """
    Main container widget for a single project's startup view.

    Structure:
    - Left side: Crew member list
    - Right side: Chat functionality
    """

    enter_edit_mode = Signal(str)  # Emits project name when entering edit mode

    def __init__(self, window, workspace: Workspace, project_name: str = None, parent=None):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        self.window = window
        self.project_name = project_name
        self.setObjectName("project_startup_widget")

        self._setup_ui()
        self._connect_signals()
        self._apply_styles()

        # Set the project info if a project name is provided
        if self.project_name:
            self.set_project(self.project_name)

    def _setup_ui(self):
        """Set up the UI components."""
        from PySide6.QtWidgets import QSplitter, QFrame
        from PySide6.QtCore import QTimer

        # Track if member double-click signal is connected
        self._member_double_clicked_connected = False

        # QML-backed host: QML owns background/chrome; QWidget content overlays on top.
        root = QWidget(self)
        root.setObjectName("project_startup_root")
        stack = QStackedLayout(root)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setStackingMode(QStackedLayout.StackAll)

        self._qml_host = QQuickWidget(root)
        self._qml_host.setObjectName("project_startup_host_qml")
        self._qml_host.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._qml_host.setAttribute(Qt.WA_TranslucentBackground, False)
        self._qml_host.setClearColor(QColor("#1e1f22"))
        qml_root_dir = Path(__file__).resolve().parent.parent.parent / "qml"
        self._qml_host.engine().addImportPath(str(qml_root_dir))
        self._qml_host.setSource(QUrl.fromLocalFile(str(PROJECT_STARTUP_HOST_QML_PATH)))
        stack.addWidget(self._qml_host)

        content = QWidget(root)
        content.setObjectName("project_startup_content")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        stack.addWidget(content)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(root)

        # Create main splitter for first level split (work area and right sidebar)
        self.main_splitter = QSplitter(Qt.Horizontal)
        # Set the main splitter to have no handle (fixed position)
        self.main_splitter.setHandleWidth(0)

        # Create the work area splitter (second level split)
        self.work_area_splitter = QSplitter(Qt.Horizontal)

        # Create the chat component (left side of work area)
        self.chat_tab = QWidget()
        self._setup_chat_tab(self.chat_tab)
        self.work_area_splitter.addWidget(self.chat_tab)

        # Create the right panel switcher for the startup window (right side of work area)
        from app.ui.window.startup.panel_switcher import StartupWindowWorkspaceTopRightBar
        self.right_panel_switcher = StartupWindowWorkspaceTopRightBar(self.workspace, self)
        self.work_area_splitter.addWidget(self.right_panel_switcher)

        # Set size policies for the work area splitter
        self.work_area_splitter.setStretchFactor(0, 1)  # Chat area expands
        self.work_area_splitter.setStretchFactor(1, 0)  # Panel area doesn't expand by default

        # Set minimum and maximum sizes for the right panel area
        # Get the right panel widget and set its size constraints
        self.right_panel_switcher.setMinimumWidth(300)
        self.right_panel_switcher.setMaximumWidth(600)

        # Add the work area splitter to the main splitter
        self.main_splitter.addWidget(self.work_area_splitter)

        # Create the right sidebar for switching between panels
        from app.ui.window.startup.right_side_bar import StartupWindowRightSideBar
        self.right_sidebar = StartupWindowRightSideBar(self.workspace, self)
        # Set fixed width for the right sidebar
        self.right_sidebar.setFixedWidth(40)
        self.main_splitter.addWidget(self.right_sidebar)

        # Set the main splitter's stretch factors
        self.main_splitter.setStretchFactor(0, 1)  # Work area expands
        self.main_splitter.setStretchFactor(1, 0)  # Sidebar stays fixed

        # Add the main splitter to the main layout
        content_layout.addWidget(self.main_splitter)

        # Connect the right sidebar button clicks to the panel switcher
        self.right_sidebar.button_clicked.connect(self.right_panel_switcher.switch_to_panel)

        # Trigger the default panel to load after the UI is set up
        QTimer.singleShot(0, lambda: self.right_sidebar.set_selected_button('members', emit_signal=True))

    def _setup_chat_tab(self, tab: QWidget):
        """Set up the chat tab."""
        # Import the agent chat component
        from app.ui.chat.agent_chat import AgentChatWidget

        # Create the agent chat component
        self.agent_chat_component = AgentChatWidget(self.workspace, tab)

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
        """Visual styles are owned by QML-backed child widgets."""
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
        # Store previous project name to detect actual project switches
        previous_project = self.project_name
        self.project_name = project_name

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

            # AgentChatWidget now owns its own QML list model/controller.
            # Avoid reaching into removed internal widgets (chat_history_widget no longer exists).

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
