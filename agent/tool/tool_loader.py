"""Tool metadata loader for parsing tool.md files."""
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ToolMetadataLoader:
    """
    Load tool metadata from tool.md files.

    This module supports:
    - Loading metadata from tool.md files with YAML frontmatter
    - Internationalization through language-suffixed files
    - Fallback to default tool.md (en_US) when language-specific file is not found

    File naming convention:
    - tool.md: English (en_US) - default/fallback
    - tool_zh_CN.md: Chinese (zh_CN)
    - tool_{lang}.md: Other languages (e.g., tool_ja_JP.md for Japanese)

    Adding a new language:
    Simply create a new file with the pattern tool_{lang}.md in the tool directory.
    No code changes required.
    """

    @staticmethod
    def load_metadata(tool_dir: Path, lang: str = "en_US"):
        """
        Load metadata for a tool from its directory.

        Args:
            tool_dir: Path to the tool directory
            lang: Language code (e.g., "en_US", "zh_CN", "ja_JP")

        Returns:
            ToolMetadata object with localized metadata

        Raises:
            FileNotFoundError: If tool.md file is not found
            ValueError: If metadata format is invalid
        """
        from .base_tool import ToolMetadata, ToolParameter

        # Determine the metadata file to load based on language
        metadata_file = ToolMetadataLoader._get_metadata_file(tool_dir, lang)

        # Parse the markdown file with YAML frontmatter
        data = ToolMetadataLoader._load_yaml_frontmatter(metadata_file)

        # Extract and validate required fields
        name = data.get("name")
        if not name:
            raise ValueError(f"Missing 'name' field in {metadata_file}")

        # Get description (plain string in new format)
        description = data.get("description", "")

        # Get return description (plain string in new format)
        return_description = data.get("return_description", "")

        # Parse parameters
        parameters = []
        for param_data in data.get("parameters", []):
            param_name = param_data.get("name")
            if not param_name:
                raise ValueError(f"Missing parameter 'name' in {metadata_file}")

            # Get parameter description (plain string in new format)
            param_description = param_data.get("description", "")

            param_type = param_data.get("type", "string")
            required = param_data.get("required", False)
            default = param_data.get("default")

            parameters.append(ToolParameter(
                name=param_name,
                description=param_description,
                param_type=param_type,
                required=required,
                default=default
            ))

        return ToolMetadata(
            name=name,
            description=description,
            parameters=parameters,
            return_description=return_description
        )

    @staticmethod
    def _get_metadata_file(tool_dir: Path, lang: str) -> Path:
        """
        Get the metadata file path for a given language.

        Args:
            tool_dir: Path to the tool directory
            lang: Language code (e.g., "en_US", "zh_CN")

        Returns:
            Path to the metadata file

        Raises:
            FileNotFoundError: If no suitable metadata file is found
        """
        # For non-English languages, try language-specific file first (e.g., tool_zh_CN.md)
        if lang != "en_US":
            lang_file = tool_dir / f"tool_{lang}.md"
            if lang_file.exists():
                return lang_file

        # Fall back to default tool.md (English)
        default_file = tool_dir / "tool.md"
        if default_file.exists():
            return default_file

        raise FileNotFoundError(f"No tool.md found in {tool_dir}")

    @staticmethod
    def _load_yaml_frontmatter(file_path: Path) -> Dict[str, Any]:
        """
        Load and parse YAML frontmatter from a markdown file.

        Args:
            file_path: Path to the markdown file

        Returns:
            Parsed YAML data as a dictionary

        Raises:
            ValueError: If file format is invalid
        """
        import re

        content = file_path.read_text(encoding="utf-8")

        # Match YAML frontmatter between --- delimiters
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            raise ValueError(f"No YAML frontmatter found in {file_path}")

        yaml_content = match.group(1)

        # Parse YAML
        try:
            import yaml
            return yaml.safe_load(yaml_content) or {}
        except ImportError:
            # Fallback to simple parsing if yaml is not available
            logger.warning("yaml module not available, using simple parsing")
            return ToolMetadataLoader._simple_yaml_parse(yaml_content)

    @staticmethod
    def _simple_yaml_parse(yaml_content: str) -> Dict[str, Any]:
        """
        Simple YAML parser for basic metadata structure.

        This is a fallback when the yaml module is not available.
        It supports a limited subset of YAML features.

        Args:
            yaml_content: YAML content as string

        Returns:
            Parsed data as a dictionary
        """
        import re

        result = {}
        current_key = None
        current_list = None
        current_dict = None
        list_item_dict = None

        for line in yaml_content.split("\n"):
            line = line.rstrip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Check for list item
            list_match = re.match(r"^-\s*(.*)", line)
            if list_match:
                item_content = list_match.group(1)

                # Initialize list if needed
                if current_key is None:
                    # Start a new list
                    current_list = []
                    current_key = "_list"
                    result[current_key] = current_list

                # Check if it's a key-value pair
                kv_match = re.match(r"(\w+):\s*(.*)", item_content)
                if kv_match:
                    key, value = kv_match.groups()
                    if list_item_dict is None:
                        list_item_dict = {}
                        current_list.append(list_item_dict)

                    # Handle different value types
                    if value.lower() in ("true", "yes"):
                        value = True
                    elif value.lower() in ("false", "no"):
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    elif value.startswith('"') or value.startswith("'"):
                        value = value[1:-1]

                    list_item_dict[key] = value
                else:
                    # Plain list item
                    if isinstance(item_content, str) and item_content.lower() in ("true", "yes"):
                        item_content = True
                    elif isinstance(item_content, str) and item_content.lower() in ("false", "no"):
                        item_content = False
                    elif isinstance(item_content, str) and item_content.isdigit():
                        item_content = int(item_content)
                    elif item_content.startswith('"') or item_content.startswith("'"):
                        item_content = item_content[1:-1]

                    current_list.append(item_content)
                    list_item_dict = None
                continue

            # Check for key-value pair
            kv_match = re.match(r"^(\w+):\s*(.*)", line)
            if kv_match:
                key, value = kv_match.groups()
                current_key = key
                current_list = None
                list_item_dict = None

                # Handle nested dict
                if not value:
                    current_dict = {}
                    result[key] = current_dict
                else:
                    current_dict = None
                    # Handle different value types
                    if value.lower() in ("true", "yes"):
                        value = True
                    elif value.lower() in ("false", "no"):
                        value = False
                    elif value.startswith('"') or value.startswith("'"):
                        value = value[1:-1]
                    elif value.isdigit():
                        value = int(value)
                    elif value == "[]":
                        value = []
                        current_list = value

                    result[key] = value
                continue

            # Check for indented key-value (nested dict)
            if line.startswith("  ") and current_dict is not None:
                nested_match = re.match(r"^\s+(\w+):\s*(.*)", line)
                if nested_match:
                    key, value = nested_match.groups()

                    # Handle different value types
                    if value.lower() in ("true", "yes"):
                        value = True
                    elif value.lower() in ("false", "no"):
                        value = False
                    elif value.startswith('"') or value.startswith("'"):
                        value = value[1:-1]
                    elif value.isdigit():
                        value = int(value)

                    current_dict[key] = value
                continue

            # Handle indented list items
            if line.startswith("  ") and current_list is not None:
                nested_match = re.match(r"^\s+-\s*(\w+):\s*(.*)", line)
                if nested_match:
                    key, value = nested_match.groups()

                    if list_item_dict is None:
                        list_item_dict = {}
                        current_list.append(list_item_dict)

                    # Handle different value types
                    if value.lower() in ("true", "yes"):
                        value = True
                    elif value.lower() in ("false", "no"):
                        value = False
                    elif value.startswith('"') or value.startswith("'"):
                        value = value[1:-1]
                    elif value.isdigit():
                        value = int(value)

                    list_item_dict[key] = value
                continue

        # Remove the temporary _list key if it exists
        if "_list" in result:
            result[list(result.keys()).index("_list")] = result.pop("_list")

        return result
