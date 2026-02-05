import shutil
import random
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional, Any

from agent.crew.crew_member import CrewMember
from agent.crew.crew_title import sort_crew_members_by_title_importance, CrewTitle
from agent.soul.soul_service import SoulService
from utils.i18n_utils import translation_manager


class CrewService:
    """
    Singleton service to manage crew members per project.

    This service handles:
    - Creating project-level crew members using write_project_crew_member
    - Updating project-level crew members using update_project_crew_member
    - Deleting project-level crew members using delete_project_crew_member
    - Reading and loading crew members from project directories
    - Managing crew member lifecycle per project
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CrewService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._project_agents: Dict[str, Dict[str, CrewMember]] = {}
        self._initialized = True

        # Connect to language change signal to reload crew members when language changes
        translation_manager.language_changed.connect(self._on_language_changed)

    def initialize_project_crew_members(self, project: Any) -> List[str]:
        """
        Ensure the project's crew directory exists and seeded from system defaults.
        Creates default crew members based on crew titles with randomly assigned matching souls.
        """
        import yaml

        project_path = _resolve_project_path(project)
        if not project_path:
            return []

        crew_members_dir = Path(project_path) / "agent" / "crew_members"
        crew_members_dir.mkdir(parents=True, exist_ok=True)

        # Get all available souls
        # Using the singleton instance - need to pass project_name to get souls
        from agent.soul import soul_service
        # Ensure the soul service is set up with the workspace
        if soul_service.workspace is None and hasattr(project, 'workspace'):
            soul_service.setup(project.workspace)

        # Use the project's name as the identifier
        project_name = getattr(project, 'project_name', getattr(project, 'name', 'default_project'))
        all_souls = soul_service.get_all_souls(project_name)

        # Get crew titles using the dedicated method
        crew_title_objects = self.get_crew_titles()

        if not crew_title_objects:
            return []

        initialized_files = []

        # Create crew members based on crew titles with matching souls
        for crew_title_obj in crew_title_objects:
            # Use the crew title name from the object
            crew_title = crew_title_obj.title

            # Find souls that match the crew title
            matching_souls = [soul for soul in all_souls if
                              soul.metadata and soul.metadata.get('crew_title') == crew_title]

            # If no matching souls found, use any soul with the crew title in its name
            if not matching_souls:
                matching_souls = [soul for soul in all_souls if
                                  crew_title in soul.name.lower() or
                                  (soul.metadata and crew_title in soul.metadata.get('name', '').lower())]

            # If still no matching souls, use all souls
            if not matching_souls:
                matching_souls = all_souls

            # Randomly select a soul from matching souls
            selected_soul = random.choice(matching_souls) if matching_souls else None

            # Get crew title metadata
            from .crew_title import CrewTitle
            crew_title_metadata = CrewTitle.get_crew_title_metadata(crew_title)

            # Prepare crew member data
            if selected_soul:
                # Create metadata for the crew member
                soul_name_for_filename = selected_soul.name.replace(' ', '_').replace('-', '_').lower()
                name_from_soul_meta = selected_soul.metadata.get('name', soul_name_for_filename) if selected_soul.metadata else soul_name_for_filename

                # Set up the crew member data with attributes from both crew title and soul
                # Soul attributes take priority over crew title attributes, but for skills we want to merge
                soul_skills = selected_soul.metadata.get('skills', []) if selected_soul.metadata else []
                crew_title_skills = crew_title_metadata.get('skills', [])

                # Merge skills from both crew title and soul, removing duplicates while preserving order
                # Start with crew title skills, then add soul skills that aren't already present
                final_skills = crew_title_skills[:]
                for skill in soul_skills:
                    if skill not in final_skills:
                        final_skills.append(skill)

                crew_member_data = {
                    'name': name_from_soul_meta,
                    'soul': selected_soul.name,
                    'crew_title': crew_title,
                    'description': selected_soul.metadata.get('description', crew_title_metadata.get('description', '')),
                    'skills': final_skills,
                    'model': selected_soul.metadata.get('model', crew_title_metadata.get('model', 'gpt-4o-mini')),
                    'temperature': selected_soul.metadata.get('temperature', crew_title_metadata.get('temperature', 0.4)),
                    'max_steps': selected_soul.metadata.get('max_steps', crew_title_metadata.get('max_steps', 5)),
                    'color': selected_soul.metadata.get('color', crew_title_metadata.get('color', '#4a90e2')),  # Soul color takes priority
                    'icon': selected_soul.metadata.get('icon', crew_title_metadata.get('icon', '🤖')),      # Soul icon takes priority
                    'prompt': ''  # Leave blank for user to customize later, will use soul knowledge dynamically
                }
            else:
                # If no soul is found, create a basic crew member with just the title
                # Use crew title metadata as fallback
                # Since no soul is involved, only use crew title skills
                crew_member_data = {
                    'name': crew_title.replace('_', ' ').title(),
                    'crew_title': crew_title,
                    'description': crew_title_metadata.get('description', f'{crew_title.replace("_", " ").title()} for the film project'),
                    'soul': '',
                    'skills': crew_title_metadata.get('skills', []),
                    'model': crew_title_metadata.get('model', 'gpt-4o-mini'),
                    'temperature': crew_title_metadata.get('temperature', 0.4),
                    'max_steps': crew_title_metadata.get('max_steps', 5),
                    'color': crew_title_metadata.get('color', '#4a90e2'),  # Use crew title color as fallback
                    'icon': crew_title_metadata.get('icon', '🤖'),        # Use crew title icon as fallback
                    'prompt': ''  # Leave blank for user to customize later
                }

            # Use the write_project_crew_member method to create the file
            file_path = self.write_project_crew_member(project, crew_member_data)
            if file_path and file_path not in initialized_files:
                initialized_files.append(file_path)

        return initialized_files

    def read_project_crew_members(self, project: Any) -> Dict[str, CrewMember]:
        """
        Read crew members from a project's crew_members directory.

        Args:
            project: The project to read crew members from

        Returns:
            Dictionary mapping crew member names to CrewMember objects
        """
        project_path = _resolve_project_path(project)
        if not project_path:
            return {}

        crew_members_dir = Path(project_path) / "agent" / "crew_members"
        if not crew_members_dir.exists():
            return {}

        workspace = getattr(project, "workspace", None)
        members: Dict[str, CrewMember] = {}

        # Load from directory
        if crew_members_dir.exists():
            for config_path in crew_members_dir.glob("*.md"):
                agent = CrewMember(
                    config_path=str(config_path),
                    workspace=workspace,
                    project=project,
                )
                members[agent.config.name] = agent

        return members

    def write_project_crew_member(self, project: Any, crew_member_data: dict) -> str:
        """
        Write a crew member to a project's crew_members directory.

        Args:
            project: The project to write the crew member to
            crew_member_data: Dictionary containing crew member information including name, description, etc.

        Returns:
            Path to the created crew member file
        """
        project_path = _resolve_project_path(project)
        if not project_path:
            return ""

        from utils.md_with_meta_utils import write_md_with_meta
        crew_members_dir = Path(project_path) / "agent" / "crew_members"
        crew_members_dir.mkdir(parents=True, exist_ok=True)

        # Extract crew member name and other data
        name = crew_member_data.get('name', '')
        crew_title = crew_member_data.get('crew_title', name.lower().replace(' ', '_'))

        # Create metadata for the crew member
        metadata = {
            'name': name,
            'soul': crew_member_data.get('soul', ''),
            'crew_title': crew_title,
            'description': crew_member_data.get('description', ''),
            'skills': crew_member_data.get('skills', []),
            'model': crew_member_data.get('model', 'gpt-4o-mini'),
            'temperature': crew_member_data.get('temperature', 0.4),
            'max_steps': crew_member_data.get('max_steps', 5),
            'color': crew_member_data.get('color', '#4a90e2'),
            'icon': crew_member_data.get('icon', '🤖')
        }

        # Generate the filename based on the crew member name
        filename = f"{crew_title}.md"
        target_file = crew_members_dir / filename

        # Write the content to the target file using the utility function
        write_md_with_meta(target_file, metadata, crew_member_data.get('prompt', ''))

        return str(target_file)

    def update_project_crew_member(self, project: Any, crew_member_name: str, crew_member_data: dict) -> bool:
        """
        Update an existing project crew member with new data.

        Args:
            project: The project containing the crew member to update
            crew_member_name: Name of the crew member to update
            crew_member_data: Dictionary containing updated crew member information

        Returns:
            True if the update was successful, False otherwise
        """
        project_path = _resolve_project_path(project)
        if not project_path:
            return False

        from utils.md_with_meta_utils import update_md_with_meta
        crew_members_dir = Path(project_path) / "agent" / "crew_members"

        # Find the crew member file by name
        crew_member_file = None
        for file_path in crew_members_dir.glob("*.md"):
            if file_path.stem == crew_member_name or file_path.stem == crew_member_data.get('crew_title', crew_member_name):
                crew_member_file = file_path
                break

        if not crew_member_file:
            return False

        # Extract crew member name and other data
        name = crew_member_data.get('name', crew_member_name)
        crew_title = crew_member_data.get('crew_title', name.lower().replace(' ', '_'))

        # Create metadata for the crew member
        metadata = {
            'name': name,
            'soul': crew_member_data.get('soul', ''),
            'crew_title': crew_title,
            'description': crew_member_data.get('description', ''),
            'skills': crew_member_data.get('skills', []),
            'model': crew_member_data.get('model', 'gpt-4o-mini'),
            'temperature': crew_member_data.get('temperature', 0.4),
            'max_steps': crew_member_data.get('max_steps', 5),
            'color': crew_member_data.get('color', '#4a90e2'),
            'icon': crew_member_data.get('icon', '🤖')
        }

        # Update the content to the target file using the utility function
        return update_md_with_meta(crew_member_file, metadata, crew_member_data.get('prompt', ''))

    def delete_project_crew_member(self, project: Any, crew_member_name: str) -> bool:
        """
        Delete an existing project crew member.

        Args:
            project: The project containing the crew member to delete
            crew_member_name: Name of the crew member to delete

        Returns:
            True if the deletion was successful, False otherwise
        """
        project_path = _resolve_project_path(project)
        if not project_path:
            return False

        crew_members_dir = Path(project_path) / "agent" / "crew_members"

        # Find the crew member file by name
        crew_member_file = None
        for file_path in crew_members_dir.glob("*.md"):
            if file_path.stem == crew_member_name:
                crew_member_file = file_path
                break

        if not crew_member_file:
            return False

        # Remove the file
        try:
            crew_member_file.unlink()
            return True
        except OSError:
            return False

    def load_project_crew_members(self, project: Any, refresh: bool = False) -> Dict[str, CrewMember]:
        """
        Load crew members for a project, initializing defaults if needed.
        """
        project_key = _resolve_project_key(project)
        if not project_key:
            return {}

        if not refresh and project_key in self._project_agents:
            return self._project_agents[project_key]

        project_path = _resolve_project_path(project)
        if not project_path:
            return {}

        self.initialize_project_crew_members(project)

        # Read crew members from the project
        members = self.read_project_crew_members(project)

        self._project_agents[project_key] = members
        return members

    def _on_language_changed(self, language_code: str):
        """Handle language change by clearing cached crew members so they reload with new language"""
        # Clear the cache to force reloading with new language
        self._project_agents.clear()

        # Log the language change
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Language changed to {language_code}, crew members will reload on next access")

    def get_crew_member(self, project: Any, name: str) -> Optional[CrewMember]:
        agents = self.load_project_crew_members(project)
        return agents.get(name)

    def get_crew_titles(self) -> List['CrewTitle']:
        """
        Get all available crew titles from the system directory based on current language.
        This allows for dynamic crew titles based on the language-specific files.

        Returns:
            List of CrewTitle objects in the order they appear in the system directory
        """
        from utils.i18n_utils import translation_manager
        from .crew_title import CrewTitle  # Import here to avoid circular import

        # Determine the language-specific system directory
        current_language = translation_manager.get_current_language()
        system_base_dir = Path(__file__).parent / "system"

        # Use language-specific directory if available, otherwise fallback to base directory
        if current_language == "zh_CN":
            system_dir = system_base_dir / "zh_CN"
        elif current_language == "en_US":
            system_dir = system_base_dir / "en_US"
        else:
            # Default to English if language not supported
            system_dir = system_base_dir / "en_US"

        # Fallback to base directory if language-specific directory doesn't exist
        if not system_dir.exists():
            system_dir = system_base_dir

        if not system_dir.exists():
            return []

        # Get all crew titles as CrewTitle objects from the filenames (without extension)
        crew_titles = []
        for system_file in system_dir.glob("*.md"):
            crew_title_name = system_file.stem
            # Create a CrewTitle object for each title
            crew_title_obj = CrewTitle.create_from_title(crew_title_name)
            if crew_title_obj and crew_title_obj.title:  # Only add if successfully created
                crew_titles.append(crew_title_obj)

        return crew_titles

    def list_crew_members(self, project: Any) -> List[CrewMember]:
        crew_members = self.load_project_crew_members(project)
        return sort_crew_members_by_title_importance(crew_members)

    def refresh_project_crew_members(self, project: Any) -> Dict[str, CrewMember]:
        return self.load_project_crew_members(project, refresh=True)

    def get_project_crew_members(self, project: Any) -> Dict[str, 'CrewMember']:
        """
        Get all crew members for a project.

        Args:
            project: The project to get crew members for

        Returns:
            Dictionary mapping agent names to their CrewMember objects
        """
        return self.load_project_crew_members(project)


def _resolve_project_path(project: Any) -> Optional[str]:
    if project is None:
        return None
    if hasattr(project, "project_path"):
        return project.project_path
    if isinstance(project, str):
        return project
    return None


def _resolve_project_key(project: Any) -> Optional[str]:
    if project is None:
        return None
    if hasattr(project, "project_path"):
        return project.project_path
    if hasattr(project, "project_name"):
        return project.project_name
    if isinstance(project, str):
        return project
    return None
