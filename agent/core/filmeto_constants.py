"""
Filmeto Agent Constants Module

Contains constants, regex patterns, and configuration values used throughout
the FilmetoAgent system.
"""
import re

# Pattern for @mentions supporting multiple languages including Chinese, Japanese, Korean, etc.
# Matches: letters, numbers, underscores, hyphens, and CJK characters (Chinese, Japanese, Korean)
# Examples: @director, @导演, @cinematographer, @分镜师
MENTION_PATTERN = re.compile(r"@([\w\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af_-]+)")

# Default producer name
PRODUCER_NAME = "producer"

# Default model configuration
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_STREAMING = True

# History configuration
DEFAULT_MAX_HISTORY = 20
DEFAULT_TRUNCATE_LIMIT = 160

# Content ID prefixes
CONTENT_ID_PREFIX_META = "meta:"
