"""Crew member metadata resolver for chat list.

This module handles loading and resolving crew member metadata including
colors, icons, and localized display names.
"""

import logging
from typing import Dict, Any, Optional, Tuple

from agent.crew.crew_title import CrewTitle

logger = logging.getLogger(__name__)


class MetadataResolver:
    """Manages crew member metadata resolution and caching.

    This class handles:
    - Loading crew member metadata from the project
    - Caching crew member data for quick lookups
    - Resolving agent colors, icons, and display names
    - Localizing crew titles

    Attributes:
        _crew_member_metadata: Cached crew member data by sender name
    """

    def __init__(self, workspace):
        """Initialize the metadata resolver.

        Args:
            workspace: Workspace instance for accessing project data
        """
        self._workspace = workspace
        self._crew_member_metadata: Dict[str, Any] = {}

    def load_crew_member_metadata(self) -> None:
        """Load crew member metadata from the current project.

        Clears and repopulates the internal metadata cache with crew members
        from the current workspace project.
        """
        try:
            from agent.crew.crew_service import CrewService

            project = self._workspace.get_project()
            if project:
                crew_member_service = CrewService()
                crew_members = crew_member_service.get_project_crew_members(project)
                self._crew_member_metadata = {}
                for name, crew_member in crew_members.items():
                    self._crew_member_metadata[crew_member.config.name.lower()] = crew_member
            else:
                self._crew_member_metadata = {}
        except Exception as e:
            logger.error(f"Error loading crew members: {e}")
            self._crew_member_metadata = {}

    def resolve_agent_metadata(
        self,
        sender: str,
        message_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Resolve agent color, icon, and metadata.

        Args:
            sender: The sender name/ID to resolve
            message_metadata: Optional metadata from the message (fallback)

        Returns:
            A tuple of (agent_color, agent_icon, crew_member_data)
        """
        if not self._crew_member_metadata:
            self.load_crew_member_metadata()

        agent_color = "#4a90e2"
        agent_icon = "🤖"
        crew_member_data: Dict[str, Any] = {}

        normalized_sender = sender.lower()
        sender_crew_member = self._crew_member_metadata.get(normalized_sender)
        if sender_crew_member:
            agent_color = sender_crew_member.config.color
            agent_icon = sender_crew_member.config.icon
            crew_title_raw = sender_crew_member.config.metadata.get("crew_title", normalized_sender)

            # Get localized display name for crew title
            crew_title_display = self._get_crew_title_display(crew_title_raw)

            crew_member_data = {
                "name": sender_crew_member.config.name,
                "description": sender_crew_member.config.description,
                "color": agent_color,
                "icon": agent_icon,
                "crew_title": crew_title_raw,
                "crew_title_display": crew_title_display,
            }
        else:
            if message_metadata:
                agent_color = message_metadata.get("color", agent_color)
                agent_icon = message_metadata.get("icon", agent_icon)
                crew_title_raw = message_metadata.get("crew_title", normalized_sender)
                crew_title_display = self._get_crew_title_display(crew_title_raw)
                crew_member_data = dict(message_metadata)
                crew_member_data["crew_title_display"] = crew_title_display
        return agent_color, agent_icon, crew_member_data

    def _get_crew_title_display(self, crew_title: str) -> str:
        """Get localized display name for crew title.

        Args:
            crew_title: The raw crew title string

        Returns:
            Localized display name for the crew title
        """
        try:
            crew_title_obj = CrewTitle.create_from_title(crew_title)
            return crew_title_obj.get_title_display()
        except Exception:
            # Fallback to formatted title (replace underscores with spaces, title case)
            return crew_title.replace("_", " ").title() if crew_title else ""
