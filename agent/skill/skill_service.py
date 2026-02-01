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
from agent.skill.skill_models import Skill, SkillParameter

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
    
    def load_skills(self):
        """
        Load all skills from system and workspace directories.
        """
        # Load system skills
        self._load_skills_from_directory(self.system_skills_path, "system")
        
        # Load custom skills from workspace if available
        if self.custom_skills_path and os.path.exists(self.custom_skills_path):
            self._load_skills_from_directory(self.custom_skills_path, "custom")
    
    def _load_skills_from_directory(self, directory_path: str, skill_type: str):
        """
        Load skills from a specific directory.
        
        Args:
            directory_path: Path to directory containing skill subdirectories
            skill_type: Type of skills being loaded ('system' or 'custom')
        """
        if not os.path.exists(directory_path):
            return
        
        for skill_dir_name in os.listdir(directory_path):
            skill_path = os.path.join(directory_path, skill_dir_name)
            
            # Check if it's a directory
            if os.path.isdir(skill_path):
                skill = self._load_skill_from_directory(skill_path)
                
                if skill:
                    # If custom skill has same name as system skill, custom takes precedence
                    self.skills[skill.name] = skill
                    print(f"Loaded {skill_type} skill: {skill.name}")
    
    def _load_skill_from_directory(self, skill_path: str) -> Optional[Skill]:
        """
        Load a single skill from its directory.
        
        Args:
            skill_path: Path to the skill directory
            
        Returns:
            Skill object if successfully loaded, None otherwise
        """
        skill_md_path = os.path.join(skill_path, "SKILL.md")
        
        if not os.path.exists(skill_md_path):
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
                print(f"Warning: Missing name or description in SKILL.md for {skill_path}")
                return None
            
            # Parse parameters if present
            parameters = []
            params_data = meta_dict.get('parameters', [])
            if isinstance(params_data, list):
                for param_info in params_data:
                    if isinstance(param_info, dict):
                        param = SkillParameter(
                            name=param_info.get('name', ''),
                            param_type=param_info.get('type', 'string'),
                            required=param_info.get('required', False),
                            default=param_info.get('default'),
                            description=param_info.get('description', '')
                        )
                        parameters.append(param)
            
            # Look for optional files
            reference_path = os.path.join(skill_path, "reference.md")
            reference = None
            if os.path.exists(reference_path):
                with open(reference_path, 'r', encoding='utf-8') as f:
                    reference = f.read()
            
            example_path = os.path.join(skill_path, "example.md")
            examples = None
            if os.path.exists(example_path):
                with open(example_path, 'r', encoding='utf-8') as f:
                    examples = f.read()
            
            # Look for scripts
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
                scripts=scripts,
                parameters=parameters
            )
            
            return skill
            
        except Exception as e:
            logger.error(f"Error loading skill from {skill_path}: {e}", exc_info=True)
            return None
    
    def get_skill(self, name: str) -> Optional[Skill]:
        """
        Get a skill by its name.
        
        Args:
            name: Name of the skill to retrieve
            
        Returns:
            Skill object if found, None otherwise
        """
        return self.skills.get(name)
    
    def get_all_skills(self) -> List[Skill]:
        """
        Get all loaded skills.
        
        Returns:
            List of all Skill objects
        """
        return list(self.skills.values())
    
    def get_skill_names(self) -> List[str]:
        """
        Get names of all loaded skills.
        
        Returns:
            List of skill names
        """
        return list(self.skills.keys())

    def get_skill_prompt_info(self, skill_name: str) -> str:
        """
        Get formatted information about a skill for use in prompts.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Formatted string describing the skill
        """
        skill = self.get_skill(skill_name)
        if not skill:
            return f"Skill '{skill_name}' not found."
        
        lines = [
            f"### Skill: {skill.name}",
            f"Description: {skill.description}",
            "",
            skill.get_parameters_prompt(),
            "",
            "Example call:",
            "```json",
            skill.get_example_call(),
            "```",
        ]
        
        if skill.knowledge:
            lines.extend(["", "Details:", skill.knowledge[:500] + "..." if len(skill.knowledge) > 500 else skill.knowledge])
        
        return "\n".join(lines)
    
    def refresh_skills(self):
        """
        Refresh the list of skills by reloading from directories.
        """
        self.skills.clear()
        self.load_skills()

    def create_skill(self, skill: Skill) -> bool:
        """
        Create a new skill using md_with_meta_utils to write the SKILL.md file.

        Args:
            skill: Skill object to create

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
            'parameters': [
                {
                    'name': param.name,
                    'type': param.param_type,
                    'required': param.required,
                    'default': param.default,
                    'description': param.description
                }
                for param in skill.parameters
            ]
        }

        # Write the SKILL.md file using md_with_meta_utils
        skill_md_path = os.path.join(skill_dir, "SKILL.md")
        try:
            write_md_with_meta(skill_md_path, metadata, skill.knowledge)

            # Save optional files if they exist
            if skill.reference:
                ref_path = os.path.join(skill_dir, "reference.md")
                with open(ref_path, 'w', encoding='utf-8') as f:
                    f.write(skill.reference)

            if skill.examples:
                example_path = os.path.join(skill_dir, "example.md")
                with open(example_path, 'w', encoding='utf-8') as f:
                    f.write(skill.examples)

            # Reload skills to include the new one
            self.refresh_skills()
            return True
        except Exception as e:
            logger.error(f"Error creating skill '{skill.name}': {e}", exc_info=True)
            return False

    def update_skill(self, skill_name: str, updated_skill: Skill) -> bool:
        """
        Update an existing skill using md_with_meta_utils to update the SKILL.md file.

        Args:
            skill_name: Name of the skill to update
            updated_skill: Updated Skill object

        Returns:
            True if update was successful, False otherwise
        """
        from utils.md_with_meta_utils import update_md_with_meta

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

        skill_md_path = os.path.join(skill_dir, "SKILL.md")

        if not os.path.exists(skill_md_path):
            print(f"SKILL.md not found for {skill_name}")
            return False

        # Prepare metadata for the updated skill
        metadata = {
            'name': updated_skill.name,
            'description': updated_skill.description,
            'parameters': [
                {
                    'name': param.name,
                    'type': param.param_type,
                    'required': param.required,
                    'default': param.default,
                    'description': param.description
                }
                for param in updated_skill.parameters
            ]
        }

        try:
            # Update the SKILL.md file using md_with_meta_utils
            success = update_md_with_meta(skill_md_path, metadata, updated_skill.knowledge)

            if success:
                # Update optional files if they exist
                if updated_skill.reference:
                    ref_path = os.path.join(skill_dir, "reference.md")
                    with open(ref_path, 'w', encoding='utf-8') as f:
                        f.write(updated_skill.reference)

                if updated_skill.examples:
                    example_path = os.path.join(skill_dir, "example.md")
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