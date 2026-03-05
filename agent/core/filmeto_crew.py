"""
Filmeto Agent Crew Manager Module

Manages crew member loading, registration, and lookup operations.
"""
import logging
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from agent.core.filmeto_constants import MENTION_PATTERN, PRODUCER_NAME
from agent.crew.crew_title import sort_crew_members_by_title_importance, CrewTitle

if TYPE_CHECKING:
    from agent.crew.crew_member import CrewMember
    from agent.crew.crew_service import CrewService

logger = logging.getLogger(__name__)


class FilmetoCrewManager:
    """
    Manages crew members for FilmetoAgent.
    Handles loading, registration, and lookup of crew members.
    """

    def __init__(self, crew_member_service: Optional["CrewService"] = None):
        """Initialize the crew manager."""
        self.crew_members: Dict[str, "CrewMember"] = {}
        self._crew_member_lookup: Dict[str, "CrewMember"] = {}
        self._crew_member_service = crew_member_service

    def set_service(self, service: "CrewService") -> None:
        """Set the crew member service."""
        self._crew_member_service = service

    def load_crew_members(self, project: Any, refresh: bool = False) -> Dict[str, "CrewMember"]:
        """
        Load crew members for a project.

        Args:
            project: The project object
            refresh: Whether to refresh the cache

        Returns:
            Dict of crew members (name -> CrewMember)
        """
        if not project or not self._crew_member_service:
            self.crew_members = {}
            self._crew_member_lookup = {}
            return {}

        crew_members = self._crew_member_service.load_project_crew_members(project, refresh=refresh)
        self.crew_members = crew_members
        self._build_lookup_table()

        return crew_members

    def _build_lookup_table(self) -> None:
        """Build the crew member lookup table with multiple keys."""
        self._crew_member_lookup = {}

        for name, member in self.crew_members.items():
            # Add the agent by its name (current behavior)
            self._crew_member_lookup[name.lower()] = member

            # Add the agent by its crew title (if available in metadata)
            crew_title = member.config.metadata.get("crew_title") if member.config.metadata else None
            if crew_title:
                self._crew_member_lookup[crew_title.lower()] = member

                # Also add display names (localized titles) for mention matching
                # This allows mentioning by localized title like @导演, @分镜师, etc.
                title_instance = CrewTitle.create_from_title(crew_title)
                if title_instance:
                    # Get display name in current language
                    display_name = title_instance.get_title_display()
                    if display_name and display_name != title_instance.title:
                        self._crew_member_lookup[display_name] = member

                    # Also add all available display names for cross-language mentions
                    if title_instance.display_names:
                        for lang, lang_display_name in title_instance.display_names.items():
                            if lang_display_name and lang_display_name not in self._crew_member_lookup:
                                self._crew_member_lookup[lang_display_name] = member

    def register_crew_member(self, member: "CrewMember") -> None:
        """Register a crew member."""
        self.crew_members[member.config.name] = member
        self._build_lookup_table()

    def get_member(self, member_id: str) -> Optional["CrewMember"]:
        """Get a member by ID."""
        return self.crew_members.get(member_id)

    def list_members(self) -> List["CrewMember"]:
        """List all registered members, sorted by crew title importance."""
        return sort_crew_members_by_title_importance(list(self.crew_members.values()))

    def get_producer(self) -> Optional["CrewMember"]:
        """Get the producer crew member."""
        return self._crew_member_lookup.get(PRODUCER_NAME)

    def lookup_member(self, key: str) -> Optional["CrewMember"]:
        """Look up a crew member by key (name, title, or display name)."""
        # Direct lookup
        member = self._crew_member_lookup.get(key)
        if member:
            return member

        # Case-insensitive lookup
        key_lower = key.lower()
        for lookup_key, agent in self._crew_member_lookup.items():
            if lookup_key.lower() == key_lower:
                return agent

        return None

    def extract_mentions(self, content: str) -> List[str]:
        """Extract @mentions from content."""
        if not content:
            return []
        return [match.group(1) for match in MENTION_PATTERN.finditer(content)]

    def resolve_mentioned_crew_member(self, content: str) -> Optional["CrewMember"]:
        """Resolve a crew member by @mention in content."""
        for mention in self.extract_mentions(content):
            member = self.lookup_member(mention.lower())
            if member:
                return member
        return None

    def resolve_mentioned_title(self, content: str) -> Optional["CrewMember"]:
        """Resolve a crew member by @mention (supports multilingual titles)."""
        return self.resolve_mentioned_crew_member(content)

    def find_member_name(self, member_name: str) -> Optional[str]:
        """
        Find the actual member name using case-insensitive comparison.

        Args:
            member_name: The member name to look up

        Returns:
            The actual member name or None if not found
        """
        for name in self.crew_members:
            if name.lower() == member_name.lower():
                return name
        return None
