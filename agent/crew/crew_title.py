"""
Module for managing crew titles and their importance in film production.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import yaml
from utils.i18n_utils import translation_manager


class CrewTitle:
    """
    Class representing different crew titles in film production with their importance levels.
    Loads crew titles dynamically from system MD files based on current language.
    """

    # Cache for storing metadata by language and title
    _metadata_cache: Dict[str, Dict[str, Any]] = {}

    def __init__(self, title: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a CrewTitle instance.

        Args:
            title: The crew title string
            metadata: Optional metadata loaded from the MD file
        """
        self.title = title
        self.metadata = metadata or {}

        # Initialize properties from metadata
        self.name = self.metadata.get('name', title)
        self.description = self.metadata.get('description', '')
        self.soul = self.metadata.get('soul', '')
        self.skills = self.metadata.get('skills', [])
        self.model = self.metadata.get('model', 'gpt-4o-mini')
        self.temperature = self.metadata.get('temperature', 0.4)
        self.max_steps = self.metadata.get('max_steps', 5)
        self.color = self.metadata.get('color', '#4a90e2')
        self.icon = self.metadata.get('icon', '🤖')
        self.display_names = self.metadata.get('display_names', {})
        self.crew_title = self.metadata.get('crew_title', title)

    @classmethod
    def get_all_dynamic_titles(cls, language: Optional[str] = None) -> List[str]:
        """
        Get all crew titles dynamically from the system directory based on current language.
        This allows for flexible crew titles defined by the language-specific files.

        Args:
            language: Language code to use (defaults to current language)

        Returns:
            List of crew title strings from the system directory
        """
        # Use provided language or get current language
        current_language = language or translation_manager.get_current_language()

        # Determine the language-specific system directory
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

        # Get all crew titles from the filenames (without extension)
        crew_titles = []
        for system_file in system_dir.glob("*.md"):
            crew_title = system_file.stem
            if crew_title not in crew_titles:  # Avoid duplicates
                crew_titles.append(crew_title)

        return crew_titles

    @classmethod
    def get_crew_title_metadata(cls, title: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metadata for a specific crew title from the system MD file.

        Args:
            title: The crew title to get metadata for
            language: Language code to use (defaults to current language)

        Returns:
            Dictionary containing the metadata from the MD file
        """
        # Use provided language or get current language
        current_language = language or translation_manager.get_current_language()

        # Create cache key with both language and title
        cache_key = f"{current_language}:{title}"

        # Check if metadata is already cached
        if cache_key in cls._metadata_cache:
            return cls._metadata_cache[cache_key]

        # Determine the language-specific system directory
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
            # Cache empty result
            cls._metadata_cache[cache_key] = {}
            return {}

        # Look for the MD file corresponding to the title
        md_file_path = system_dir / f"{title}.md"
        if not md_file_path.exists():
            # Cache empty result
            cls._metadata_cache[cache_key] = {}
            return {}

        # Use the new utility function to read the metadata
        from utils.md_with_meta_utils import get_metadata
        metadata = get_metadata(md_file_path)

        # Cache the result
        cls._metadata_cache[cache_key] = metadata
        return metadata

    @classmethod
    def create_from_title(cls, title: str, language: Optional[str] = None) -> 'CrewTitle':
        """
        Create a CrewTitle instance from a title string, loading its metadata.

        Args:
            title: The crew title string
            language: Language code to use (defaults to current language)

        Returns:
            CrewTitle instance with loaded metadata
        """
        metadata = cls.get_crew_title_metadata(title, language)
        return cls(title, metadata)

    def get_title_display(self, lang_code: str = None) -> str:
        """Get the display title for the crew position in the specified language."""
        # Use current language if not provided
        if lang_code is None:
            lang_code = translation_manager.get_current_language()
            # Map language code to display names key format
            # "zh_CN" -> "zh", "en_US" -> "en"
            if lang_code == "zh_CN":
                lang_code = "zh"
            elif lang_code == "en_US":
                lang_code = "en"

        # Use the display names from the metadata if available
        if self.display_names and lang_code in self.display_names:
            return self.display_names[lang_code]

        # Fallback to hardcoded mappings if not in metadata
        titles = {
            "director": {
                "en": "Director",
                "zh": "导演"
            },
            "cinematographer": {
                "en": "Cinematographer",
                "zh": "摄影师"
            },
            "editor": {
                "en": "Editor",
                "zh": "剪辑师"
            },
            "producer": {
                "en": "Producer",
                "zh": "制片人"
            },
            "screenwriter": {
                "en": "Screenwriter",
                "zh": "编剧"
            },
            "storyboard_artist": {
                "en": "Storyboard Artist",
                "zh": "分镜师"
            },
            "vfx_supervisor": {
                "en": "VFX Supervisor",
                "zh": "视觉特效总监"
            },
            "sound_designer": {
                "en": "Sound Designer",
                "zh": "声音设计师"
            },
            "other": {
                "en": "Other",
                "zh": "其他"
            }
        }

        title_dict = titles.get(self.title, {})
        return title_dict.get(lang_code, title_dict.get("en", self.title))

    @classmethod
    def get_importance_order(cls, use_dynamic: bool = False, language: Optional[str] = None) -> List[str]:
        """
        Get the importance order of crew titles as a list of strings.

        Args:
            use_dynamic: If True, use dynamic titles from system directory;
                        if False, use the static default order (for backward compatibility)
            language: Language code to use (defaults to current language)

        Returns:
            List of crew title strings in order of importance (most important first)
        """
        if use_dynamic:
            # Return dynamic titles from system directory
            return cls.get_all_dynamic_titles(language)
        else:
            # Return static default order for backward compatibility
            return ["producer", "director", "screenwriter", "cinematographer", "editor",
                    "sound_designer", "vfx_supervisor", "storyboard_artist", "other"]

    @classmethod
    def get_title_importance_rank(cls, title: str, use_dynamic: bool = False, language: Optional[str] = None) -> int:
        """
        Get the importance rank of a crew title (lower number means higher importance).

        Args:
            title: The crew title string to check
            use_dynamic: If True, use dynamic titles from system directory;
                        if False, use the static enum order (for backward compatibility)
            language: Language code to use (defaults to current language)

        Returns:
            Integer rank (0 for most important, higher numbers for less important)
            Returns len(get_importance_order()) for unknown titles
        """
        importance_order = cls.get_importance_order(use_dynamic=use_dynamic, language=language)
        try:
            return importance_order.index(title)
        except ValueError:
            # If the title is not in our predefined list, assign lowest importance
            return len(importance_order)

    @classmethod
    def from_string(cls, title: str, language: Optional[str] = None) -> Optional['CrewTitle']:
        """
        Create a CrewTitle from a string representation.

        Args:
            title: String representation of the crew title
            language: Language code to use (defaults to current language)

        Returns:
            CrewTitle instance or None if not found
        """
        # Create a CrewTitle instance with metadata loaded from the system file
        crew_title = cls.create_from_title(title, language)
        # Return the instance only if it has valid data
        if crew_title.title:
            return crew_title
        return None

    @classmethod
    def is_valid_title(cls, title: str, language: Optional[str] = None) -> bool:
        """
        Check if a given string is a valid crew title.

        Args:
            title: String to check
            language: Language code to use (defaults to current language)

        Returns:
            True if the title is valid, False otherwise
        """
        # Check if the title exists in the dynamic list of titles
        all_titles = cls.get_all_dynamic_titles(language)
        return title in all_titles


def sort_crew_members_by_title_importance(crew_members, use_dynamic: bool = False, language: Optional[str] = None) -> List:
    """
    Sort crew members based on the importance of their crew titles.

    Args:
        crew_members: List or dictionary of crew members to sort
        use_dynamic: If True, use dynamic titles from system directory;
                    if False, use the static enum order (for backward compatibility)
        language: Language code to use (defaults to current language)

    Returns:
        Sorted list of crew members based on title importance
    """
    def get_importance_rank(crew_member):
        # Get the crew title from the crew member's metadata
        crew_title = getattr(crew_member, 'config', {}).metadata.get('crew_title', 'other')
        return CrewTitle.get_title_importance_rank(crew_title, use_dynamic=use_dynamic, language=language)

    # If it's a dictionary, convert to list of values
    if isinstance(crew_members, dict):
        crew_list = list(crew_members.values())
    else:
        crew_list = list(crew_members)

    # Sort based on importance rank
    sorted_crew = sorted(crew_list, key=get_importance_rank)
    return sorted_crew