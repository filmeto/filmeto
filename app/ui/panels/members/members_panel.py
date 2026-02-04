"""
Members Panel

This module implements a panel for displaying agent chat members that can be used
in both startup and edit windows.
"""
from PySide6.QtWidgets import QVBoxLayout

from app.ui.panels.base_panel import BasePanel
from app.ui.chat.agent_chat_members import AgentChatMembersWidget
from utils.i18n_utils import tr, translation_manager


class MembersPanel(BasePanel):
    """Panel for displaying agent chat members."""

    def __init__(self, workspace, parent=None):
        """Initialize the members panel."""
        super().__init__(workspace, parent)
        self.set_panel_title(tr("Crew Members"))

        # Create the agent chat members component
        self.agent_chat_members_component = AgentChatMembersWidget(self.workspace)

        # Add it to the content layout
        self.content_layout.addWidget(self.agent_chat_members_component)

        # Connect to language change signal to refresh titles
        translation_manager.language_changed.connect(self._on_language_changed)

    def setup_ui(self):
        """Set up the panel UI framework."""
        # UI is already set up in the constructor
        pass

    def load_data(self):
        """Load business data for the panel."""
        # Load members data for the current project
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

            # Set the members in the members component
            self.set_members(crew_members)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading crew members: {e}")

    def set_members(self, members):
        """Set the list of crew members to display."""
        if hasattr(self.agent_chat_members_component, 'set_members'):
            self.agent_chat_members_component.set_members(members)

    def refresh_members(self):
        """Refresh the member list."""
        if hasattr(self.agent_chat_members_component, 'refresh_members'):
            self.agent_chat_members_component.refresh_members()

    def on_project_switched(self, project_name: str):
        """Called when the project is switched."""
        super().on_project_switched(project_name)
        # Reload members for the new project
        self._load_crew_members()

    def _on_language_changed(self, language_code: str):
        """Called when the language is changed."""
        # Update the panel title
        self.set_panel_title(tr("Crew Members"))
        # Reload members to refresh their displayed titles
        self._load_crew_members()