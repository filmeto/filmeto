"""JSON utility functions for extracting JSON from LLM responses."""
import json
from typing import Any, Dict, Optional


class JsonExtractor:
    """Utility class for extracting JSON from LLM responses.

    Handles various formats of JSON wrapped in markdown code blocks:
    - ```json {...} ```
    - ``` {...} ``` (without language identifier)
    - Plain JSON objects

    Uses fast string operations first, falls back to regex only when needed.
    """

    # Code block markers
    _CODE_BLOCK_START = "```"
    _CODE_BLOCK_END = "```"
    _JSON_LANG = "json"

    @classmethod
    def extract_json(cls, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON payload from text using multiple strategies.

        Strategies are ordered by performance (fastest first):
        1. Direct parse: text wrapped in braces
        2. Code block extraction via string search (```json or ```)
        3. First balanced JSON object in text

        Args:
            text: The text to extract JSON from

        Returns:
            Parsed JSON dict, or None if no valid JSON found
        """
        if not text:
            return None

        # Strategy 1: Fast path - text starts and ends with braces
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            result = cls.safe_json_load(stripped)
            if result is not None:
                return result

        # Strategy 2: Extract from code blocks using string search (no regex)
        result = cls._extract_from_code_block(text)
        if result is not None:
            return result

        # Strategy 3: Find balanced JSON in text
        json_str = cls.find_balanced_json(text)
        if json_str:
            result = cls.safe_json_load(json_str)
            if result is not None:
                return result

        return None

    @classmethod
    def _extract_from_code_block(cls, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from markdown code blocks using fast string operations.

        Handles formats:
        - ```json\n{...}\n```
        - ```\n{...}\n```

        Args:
            text: Text possibly containing code blocks

        Returns:
            Parsed JSON dict or None
        """
        # Find opening code block
        start_idx = text.find(cls._CODE_BLOCK_START)
        if start_idx == -1:
            return None

        # Move past the opening ```
        content_start = start_idx + len(cls._CODE_BLOCK_START)

        # Check for optional language identifier (json or whitespace only)
        remaining = text[content_start:]

        # Skip 'json' identifier if present
        if remaining.startswith(cls._JSON_LANG):
            content_start += len(cls._JSON_LANG)
            remaining = text[content_start:]

        # Skip whitespace/newline after opening marker
        while content_start < len(text) and text[content_start] in " \t\n":
            content_start += 1

        # Find closing code block
        end_idx = text.find(cls._CODE_BLOCK_END, content_start)
        if end_idx == -1:
            return None

        # Extract content, stripping trailing whitespace
        content = text[content_start:end_idx].rstrip()

        # Try to parse
        return cls.safe_json_load(content)

    @classmethod
    def extract_code_block_content(cls, text: str, strict: bool = False) -> Optional[str]:
        """
        Extract content from markdown code blocks without JSON parsing.

        Uses fast string search instead of regex.

        Args:
            text: The text containing code blocks
            strict: If True, only match ```json blocks; otherwise match any code block

        Returns:
            The content inside the code block, or None if not found
        """
        # Find opening code block
        start_idx = text.find(cls._CODE_BLOCK_START)
        if start_idx == -1:
            return None

        # Move past the opening ```
        content_start = start_idx + len(cls._CODE_BLOCK_START)
        remaining = text[content_start:]

        # Check for language identifier
        if remaining.startswith(cls._JSON_LANG):
            content_start += len(cls._JSON_LANG)
        elif strict:
            # In strict mode, must have 'json' identifier
            return None

        # Skip whitespace/newline after opening marker
        while content_start < len(text) and text[content_start] in " \t\n":
            content_start += 1

        # Find closing code block
        end_idx = text.find(cls._CODE_BLOCK_END, content_start)
        if end_idx == -1:
            return None

        return text[content_start:end_idx].rstrip()

    @classmethod
    def safe_json_load(cls, candidate: str) -> Optional[Dict[str, Any]]:
        """
        Safely parse JSON, returning None on failure.

        Args:
            candidate: String to parse as JSON

        Returns:
            Parsed dict if successful and result is a dict, None otherwise
        """
        try:
            payload = json.loads(candidate)
            return payload if isinstance(payload, dict) else None
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    @classmethod
    def find_balanced_json(cls, text: str) -> Optional[str]:
        """
        Find the first balanced JSON object in text.

        Args:
            text: Text to search for balanced JSON

        Returns:
            The balanced JSON string, or None if not found
        """
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        for idx in range(start, len(text)):
            if text[idx] == "{":
                depth += 1
            elif text[idx] == "}":
                depth -= 1
                if depth == 0:
                    return text[start : idx + 1]

        return None


# Convenience function for backward compatibility
def extract_json_payload(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON payload from text.

    This is a convenience function that delegates to JsonExtractor.extract_json.
    """
    return JsonExtractor.extract_json(text)


def safe_json_load(candidate: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON, returning None on failure.

    This is a convenience function that delegates to JsonExtractor.safe_json_load.
    """
    return JsonExtractor.safe_json_load(candidate)
