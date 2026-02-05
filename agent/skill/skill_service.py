"""
Skill Service Module

Implements the SkillService class to manage skills following the Claude skill specification.
Skills are organized as directories containing a SKILL.md file with metadata and knowledge,
plus optional reference.md, example.md, and scripts/ directory.
"""
import os
import logging
from typing import AsyncGenerator, Dict, List, Optional, Any, TYPE_CHECKING

# Import data models
from agent.skill.skill_models import Skill

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from agent.event.agent_event import AgentEvent


class SkillService:
    """
    Service class that manages skills following the Claude skill specification.

    Skills are organized as directories containing:
    - SKILL.md: Contains metadata (between --- markers) and knowledge
    - reference.md: Optional reference documentation
    - example.md: Optional usage examples
    - scripts/: Optional directory with executable scripts

    This service handles:
    - Reading skills using md_with_meta_utils for SKILL.md files
    - Creating new skills using create_skill with md_with_meta_utils
    - Updating existing skills using update_skill with md_with_meta_utils
    - Deleting skills using delete_skill
    - Managing skill lifecycle
    """
    
    def __init__(self, workspace=None):
        """
        Initialize the SkillService.

        Args:
            workspace: Optional Workspace object where custom skills may be located
        """
        self.workspace = workspace
        self.system_skills_path = os.path.join(os.path.dirname(__file__), "system")
        self.custom_skills_path = os.path.join(workspace.workspace_path, "skills") if workspace and hasattr(workspace, 'workspace_path') else None

        # Dictionary to store loaded skills by name
        self.skills: Dict[str, Skill] = {}

        # Initialize SkillChat for ReAct-based execution
        from agent.skill.skill_chat import SkillChat
        self._skill_chat = SkillChat(self)

        # Load all skills
        self.load_skills()
    
    def load_skills(self, language: str = None):
        """
        Load all skills from system and workspace directories.

        Args:
            language: Optional language code (e.g., 'zh_CN', 'en_US') to load
                      language-specific skill files. Falls back to default SKILL.md
                      if language-specific file not found.
        """
        # Load system skills
        self._load_skills_from_directory(self.system_skills_path, "system", language=language)

        # Load custom skills from workspace if available
        if self.custom_skills_path and os.path.exists(self.custom_skills_path):
            self._load_skills_from_directory(self.custom_skills_path, "custom", language=language)
    
    def _load_skills_from_directory(self, directory_path: str, skill_type: str, language: str = None):
        """
        Load skills from a specific directory.

        Args:
            directory_path: Path to directory containing skill subdirectories
            skill_type: Type of skills being loaded ('system' or 'custom')
            language: Optional language code for loading language-specific skill files
        """
        if not os.path.exists(directory_path):
            return

        for skill_dir_name in os.listdir(directory_path):
            skill_path = os.path.join(directory_path, skill_dir_name)

            # Check if it's a directory
            if os.path.isdir(skill_path):
                skill = self._load_skill_from_directory(skill_path, language=language)

                if skill:
                    # If custom skill has same name as system skill, custom takes precedence
                    self.skills[skill.name] = skill
                    print(f"Loaded {skill_type} skill: {skill.name}")
    
    def _load_skill_from_directory(self, skill_path: str, language: str = None) -> Optional[Skill]:
        """
        Load a single skill from its directory.

        Args:
            skill_path: Path to the skill directory
            language: Optional language code (e.g., 'zh_CN', 'en_US') to load
                      language-specific skill file. Falls back to SKILL.md if not found.

        Returns:
            Skill object if successfully loaded, None otherwise
        """
        # Determine which SKILL file to load based on language
        skill_md_path = self._get_skill_md_path(skill_path, language)

        if not skill_md_path or not os.path.exists(skill_md_path):
            print(f"Warning: SKILL.md not found in {skill_path}")
            return None

        try:
            # Use md_with_meta_utils to read the SKILL.md file
            from utils.md_with_meta_utils import read_md_with_meta
            meta_dict, knowledge = read_md_with_meta(skill_md_path)

            # Extract required fields
            name = meta_dict.get('name')
            description = meta_dict.get('description')

            if not name or not description:
                print(f"Warning: Missing name or description in {os.path.basename(skill_md_path)} for {skill_path}")
                return None

            if 'parameters' in meta_dict:
                logger.debug("Ignoring deprecated skill parameters for %s", name)

            # Look for optional language-specific files first, then default files
            reference_path = self._get_optional_file_path(skill_path, "reference", language)
            reference = None
            if reference_path and os.path.exists(reference_path):
                with open(reference_path, 'r', encoding='utf-8') as f:
                    reference = f.read()

            example_path = self._get_optional_file_path(skill_path, "example", language)
            examples = None
            if example_path and os.path.exists(example_path):
                with open(example_path, 'r', encoding='utf-8') as f:
                    examples = f.read()

            # Look for scripts (scripts are language-independent)
            scripts_dir = os.path.join(skill_path, "scripts")
            scripts = []
            if os.path.exists(scripts_dir) and os.path.isdir(scripts_dir):
                for script_file in os.listdir(scripts_dir):
                    script_path = os.path.join(scripts_dir, script_file)
                    if os.path.isfile(script_path) and script_file.endswith('.py'):
                        scripts.append(script_path)

            # Create and return the skill object
            skill = Skill(
                name=name,
                description=description,
                knowledge=knowledge,
                skill_path=skill_path,
                reference=reference,
                examples=examples,
                scripts=scripts
            )

            return skill

        except Exception as e:
            logger.error(f"Error loading skill from {skill_path}: {e}", exc_info=True)
            return None

    def _get_skill_md_path(self, skill_path: str, language: str = None) -> Optional[str]:
        """
        Get the path to the skill markdown file, trying language-specific version first.

        Args:
            skill_path: Path to the skill directory
            language: Optional language code (e.g., 'zh_CN', 'en_US')

        Returns:
            Path to the skill markdown file to use, or None if no file exists
        """
        # Try language-specific file first (e.g., SKILL_zh_CN.md)
        if language:
            lang_skill_path = os.path.join(skill_path, f"SKILL_{language}.md")
            if os.path.exists(lang_skill_path):
                return lang_skill_path

        # Fall back to default SKILL.md
        default_path = os.path.join(skill_path, "SKILL.md")
        if os.path.exists(default_path):
            return default_path

        return None

    def _get_optional_file_path(self, skill_path: str, base_name: str, language: str = None) -> Optional[str]:
        """
        Get the path to an optional file (like reference.md or example.md),
        trying language-specific version first.

        Args:
            skill_path: Path to the skill directory
            base_name: Base name of the file (e.g., 'reference', 'example')
            language: Optional language code (e.g., 'zh_CN', 'en_US')

        Returns:
            Path to the file to use, or None if no file exists
        """
        # Try language-specific file first (e.g., reference_zh_CN.md)
        if language:
            lang_path = os.path.join(skill_path, f"{base_name}_{language}.md")
            if os.path.exists(lang_path):
                return lang_path

        # Fall back to default file
        default_path = os.path.join(skill_path, f"{base_name}.md")
        if os.path.exists(default_path):
            return default_path

        return None
    
    def get_skill(self, name: str, language: str = None) -> Optional[Skill]:
        """
        Get a skill by its name.

        Args:
            name: Name of the skill to retrieve
            language: Optional language code (e.g., 'zh_CN', 'en_US') to load
                      language-specific version. If provided, loads the skill
                      from disk with the specified language.

        Returns:
            Skill object if found, None otherwise
        """
        # If language is specified, try to load the skill from disk with that language
        if language:
            # Try to find the skill directory and load it with the specified language
            for dir_path in [self.custom_skills_path, self.system_skills_path]:
                if dir_path and os.path.exists(dir_path):
                    skill_path = os.path.join(dir_path, name)
                    if os.path.exists(skill_path):
                        skill = self._load_skill_from_directory(skill_path, language=language)
                        if skill:
                            return skill

        # Return cached skill if language not specified or on-demand load failed
        return self.skills.get(name)

    def get_all_skills(self, language: str = None) -> List[Skill]:
        """
        Get all loaded skills.

        Args:
            language: Optional language code. If provided, reloads all skills
                      with the specified language before returning.

        Returns:
            List of all Skill objects
        """
        if language:
            # Reload skills with the specified language
            self.skills.clear()
            self.load_skills(language=language)
        return list(self.skills.values())
    
    def get_skill_names(self) -> List[str]:
        """
        Get names of all loaded skills.
        
        Returns:
            List of skill names
        """
        return list(self.skills.keys())

    def get_skill_prompt_info(self, skill_name: str, language: str = None) -> str:
        """
        Get formatted information about a skill for use in prompts.

        Args:
            skill_name: Name of the skill
            language: Optional language code (e.g., 'zh_CN', 'en_US') to load
                      language-specific version of the skill.

        Returns:
            Formatted string describing the skill
        """
        skill = self.get_skill(skill_name, language=language)
        if not skill:
            return f"Skill '{skill_name}' not found."

        lines = [
            f"### Skill: {skill.name}",
            f"Description: {skill.description}",
            "",
            "Invocation: Provide a prompt that includes all required details.",
            "",
            "Example call:",
            "```json",
            skill.get_example_call(),
            "```",
        ]

        if skill.knowledge:
            lines.extend(["", "Details:", skill.knowledge[:500] + "..." if len(skill.knowledge) > 500 else skill.knowledge])

        return "\n".join(lines)

    def refresh_skills(self, language: str = None):
        """
        Refresh the list of skills by reloading from directories.

        Args:
            language: Optional language code (e.g., 'zh_CN', 'en_US') to load
                      language-specific skill files.
        """
        self.skills.clear()
        self.load_skills(language=language)

    def create_skill(self, skill: Skill, language: str = None) -> bool:
        """
        Create a new skill using md_with_meta_utils to write the SKILL.md file.

        Args:
            skill: Skill object to create
            language: Optional language code (e.g., 'zh_CN', 'en_US') to create
                      language-specific version. If specified, creates SKILL_{language}.md
                      instead of SKILL.md.

        Returns:
            True if creation was successful, False otherwise
        """
        from utils.md_with_meta_utils import write_md_with_meta

        # Create the skill directory if it doesn't exist
        skill_dir = os.path.join(self.custom_skills_path or self.system_skills_path, skill.name)
        os.makedirs(skill_dir, exist_ok=True)

        # Prepare metadata for the skill
        metadata = {
            'name': skill.name,
            'description': skill.description,
        }

        # Determine the SKILL file name based on language
        skill_md_filename = f"SKILL_{language}.md" if language else "SKILL.md"
        skill_md_path = os.path.join(skill_dir, skill_md_filename)

        # Determine optional file names based on language
        ref_filename = f"reference_{language}.md" if language else "reference.md"
        example_filename = f"example_{language}.md" if language else "example.md"

        try:
            write_md_with_meta(skill_md_path, metadata, skill.knowledge)

            # Save optional files if they exist
            if skill.reference:
                ref_path = os.path.join(skill_dir, ref_filename)
                with open(ref_path, 'w', encoding='utf-8') as f:
                    f.write(skill.reference)

            if skill.examples:
                example_path = os.path.join(skill_dir, example_filename)
                with open(example_path, 'w', encoding='utf-8') as f:
                    f.write(skill.examples)

            # Reload skills to include the new one
            self.refresh_skills()
            return True
        except Exception as e:
            logger.error(f"Error creating skill '{skill.name}': {e}", exc_info=True)
            return False

    def update_skill(self, skill_name: str, updated_skill: Skill, language: str = None) -> bool:
        """
        Update an existing skill using md_with_meta_utils to update the SKILL.md file.

        Args:
            skill_name: Name of the skill to update
            updated_skill: Updated Skill object
            language: Optional language code (e.g., 'zh_CN', 'en_US') to update
                      language-specific version. If specified, updates SKILL_{language}.md
                      instead of SKILL.md.

        Returns:
            True if update was successful, False otherwise
        """
        # Find the existing skill directory
        skill_dir = None
        for dir_path in [self.system_skills_path, self.custom_skills_path]:
            if dir_path and os.path.exists(dir_path):
                candidate_path = os.path.join(dir_path, skill_name)
                if os.path.exists(candidate_path):
                    skill_dir = candidate_path
                    break

        if not skill_dir:
            print(f"Skill directory not found for {skill_name}")
            return False

        # Determine the SKILL file name based on language
        skill_md_filename = f"SKILL_{language}.md" if language else "SKILL.md"
        skill_md_path = os.path.join(skill_dir, skill_md_filename)

        # If language-specific file doesn't exist, fall back to default SKILL.md
        if not os.path.exists(skill_md_path):
            skill_md_path = os.path.join(skill_dir, "SKILL.md")

        if not os.path.exists(skill_md_path):
            print(f"{skill_md_filename} not found for {skill_name}")
            return False

        # Determine optional file names based on language
        ref_filename = f"reference_{language}.md" if language else "reference.md"
        example_filename = f"example_{language}.md" if language else "example.md"

        # Prepare metadata for the updated skill
        metadata = {
            'name': updated_skill.name,
            'description': updated_skill.description,
        }

        try:
            # Remove deprecated parameters from metadata while preserving other fields
            from utils.md_with_meta_utils import read_md_with_meta, write_md_with_meta
            current_metadata, _ = read_md_with_meta(skill_md_path)
            current_metadata.update(metadata)
            current_metadata.pop('parameters', None)

            # Update the SKILL.md file using md_with_meta_utils
            write_md_with_meta(skill_md_path, current_metadata, updated_skill.knowledge)
            success = True

            if success:
                # Update optional files if they exist
                if updated_skill.reference:
                    ref_path = os.path.join(skill_dir, ref_filename)
                    with open(ref_path, 'w', encoding='utf-8') as f:
                        f.write(updated_skill.reference)

                if updated_skill.examples:
                    example_path = os.path.join(skill_dir, example_filename)
                    with open(example_path, 'w', encoding='utf-8') as f:
                        f.write(updated_skill.examples)

                # Reload skills to include the updated one
                self.refresh_skills()

            return success
        except Exception as e:
            logger.error(f"Error updating skill '{skill_name}': {e}", exc_info=True)
            return False

    async def chat_stream(
        self,
        skill: Skill,
        user_message: Optional[str] = None,
        workspace: Any = None,
        project: Any = None,
        args: Optional[Dict[str, Any]] = None,
        llm_service: Any = None,
        max_steps: int = 10,
        crew_member_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> AsyncGenerator["AgentEvent", None]:
        """通过 React 流式执行 skill

        Args:
            skill: The Skill object to execute
            user_message: Optional user message/question
            workspace: Any object (optional)
            project: Any object (optional)
            args: Arguments to pass to the skill
            llm_service: Optional LLM service
            max_steps: Maximum number of ReAct steps
            crew_member_name: Name of the crew member calling this skill (for react_type uniqueness)
            conversation_id: Unique conversation/session ID (for react_type uniqueness)

        Yields:
            ReactEvent objects for skill execution progress
        """
        async for event in self._skill_chat.chat_stream(
            skill=skill,
            user_message=user_message,
            workspace=workspace,
            project=project,
            args=args,
            llm_service=llm_service,
            max_steps=max_steps,
            crew_member_name=crew_member_name,
            conversation_id=conversation_id,
        ):
            yield event

    def delete_skill(self, skill_name: str) -> bool:
        """
        Delete a skill by removing its directory.

        Args:
            skill_name: Name of the skill to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        import shutil

        # Find the skill directory
        skill_dir = None
        for dir_path in [self.system_skills_path, self.custom_skills_path]:
            if dir_path and os.path.exists(dir_path):
                candidate_path = os.path.join(dir_path, skill_name)
                if os.path.exists(candidate_path):
                    skill_dir = candidate_path
                    break

        if not skill_dir:
            print(f"Skill directory not found for {skill_name}")
            return False

        try:
            # Remove the entire skill directory
            shutil.rmtree(skill_dir)

            # Remove from internal cache and reload
            if skill_name in self.skills:
                del self.skills[skill_name]

            return True
        except Exception as e:
            logger.error(f"Error deleting skill '{skill_name}': {e}", exc_info=True)
            return False